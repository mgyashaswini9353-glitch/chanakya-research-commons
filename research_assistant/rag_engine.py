"""
F8 Grounded AI Research Assistant (Retrieval-Augmented Generation).
Pipeline:
  1. Embed natural-language question via SemanticEmbedder (all-MiniLM-L6-v2 / TF-IDF-SVD fallback)
  2. Hybrid retrieve top-K relevant papers and extract highest-scoring evidence passages
  3. Enforce strict sufficiency threshold — explicitly states when corpus evidence is insufficient
  4. Generate grounded answer with inline citations [1]..[K]:
     - Calls local Ollama LLM if available at OLLAMA_BASE_URL
     - Otherwise uses a deterministic Extractive-Synthesizer grounded strictly in retrieved sentences
  5. Returns verifiable citations + full retrieved passages so users can inspect every source.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.models import Paper
from ml.embeddings.embedder import cosine_similarity_matrix, get_embedder
from ml.search.search_engine import search_papers_ranked


def _split_sentences(text: str) -> List[str]:
    if not text:
        return []
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sents if len(s.strip()) >= 25]


def _score_sentence(query_tokens: set, sentence: str) -> float:
    toks = set(re.findall(r"[a-z0-9]+", sentence.lower()))
    if not toks or not query_tokens:
        return 0.0
    overlap = len(query_tokens & toks)
    return overlap / (len(query_tokens) ** 0.7)


def _try_ollama_generate(question: str, context_blocks: List[str]) -> Optional[str]:
    """Attempt grounded synthesis using a local Ollama model; returns None if Ollama isn't running."""
    prompt = (
        "You are the Chanakya Research Commons AI Assistant. "
        "Answer the user's research question using ONLY the numbered sources below. "
        "Cite sources inline using [1], [2], etc. NEVER invent papers, numbers, or facts not present in the sources. "
        "If the sources do not sufficiently answer the question, explicitly state that.\n\n"
        "SOURCES:\n"
        + "\n\n".join(context_blocks)
        + f"\n\nQUESTION: {question}\n\nGROUNDED ANSWER:"
    )
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "").strip()
                if text:
                    return text
    except Exception:
        return None
    return None


def answer_research_question(
    db: Session,
    question: str,
    top_k: int = 5,
    only_library: bool = False,
) -> Dict[str, Any]:
    q_clean = (question or "").strip()
    if len(q_clean) < 4:
        return {
            "question": q_clean,
            "sufficient_evidence": False,
            "generation_mode": "validation",
            "answer": "Please enter a complete research question so I can retrieve supporting papers from the Chanakya corpus.",
            "citations": [],
            "retrieved_passages": [],
        }

    # Step 1: Hybrid retrieval of candidate papers
    hits = search_papers_ranked(
        db=db,
        query=q_clean,
        mode="hybrid",
        only_library=only_library,
        limit=max(top_k * 2, 10),
    )

    # Filter out weakly relevant results
    stopwords = {
        "what", "which", "how", "does", "that", "this", "with", "from", "about",
        "explain", "describe", "compare", "papers", "research", "using", "based",
        "recent", "findings", "study", "methods", "approaches", "used", "applied",
        "techniques", "improve", "advances", "are", "the", "for", "and",
    }
    query_tokens = {
        t
        for t in re.findall(r"[a-z0-9]+", q_clean.lower())
        if len(t) >= 3 and t not in stopwords
    }

    embedder = get_embedder()
    q_vec = embedder.encode([q_clean])[0]

    # Step 2: Passage extraction & strict sufficiency check
    passages = []
    for hit in hits:
        abstract = hit.get("abstract") or ""
        title_text = hit.get("title") or ""
        sents = _split_sentences(abstract)
        if not sents:
            continue
        sent_vecs = embedder.encode(sents)
        sem_sims = cosine_similarity_matrix(q_vec, sent_vecs)

        doc_tokens = set(re.findall(r"[a-z0-9]+", f"{title_text} {abstract}".lower()))
        doc_term_overlap = len(query_tokens & doc_tokens)
        doc_lex_ratio = doc_term_overlap / max(1, len(query_tokens))

        scored_sents = []
        for s_idx, sent in enumerate(sents):
            lex = _score_sentence(query_tokens, sent)
            sem = max(0.0, float(sem_sims[s_idx]))
            comb = 0.55 * sem + 0.45 * min(1.0, lex)
            scored_sents.append((comb, sem, lex, sent))
        scored_sents.sort(key=lambda x: x[0], reverse=True)
        best_comb, best_sem, best_lex, best_sent = scored_sents[0]
        # Build passage snippet from top 2 sentences
        snippet = " ".join(x[3] for x in scored_sents[:2])

        # Strict grounding check: require substantive domain term overlap OR strong semantic alignment with at least 1 domain hit
        if doc_term_overlap == 0:
            continue
        if doc_lex_ratio < 0.25 and best_sem < 0.42:
            continue

        passages.append(
            {
                "paper_id": hit["id"],
                "title": hit["title"],
                "authors": hit["authors"][:4],
                "publication_year": hit["publication_year"],
                "venue": hit["venue"],
                "primary_source": hit["primary_source"],
                "sources": [s.get("source") for s in (hit.get("sources") or []) if isinstance(s, dict)],
                "in_university_library": hit["in_university_library"],
                "save_count": hit["save_count"],
                "url": hit["url"],
                "doi": hit["doi"],
                "passage": snippet,
                "best_sentence": best_sent,
                "passage_score": round(float(best_comb), 4),
                "semantic_score": round(float(best_sem), 4),
                "lexical_score": round(float(best_lex), 4),
            }
        )

    passages.sort(key=lambda x: x["passage_score"], reverse=True)
    top_passages = passages[:top_k]

    if not top_passages or (top_passages[0]["semantic_score"] < 0.22 and top_passages[0]["lexical_score"] < 0.28):
        return {
            "question": q_clean,
            "sufficient_evidence": False,
            "generation_mode": "insufficient_evidence",
            "answer": (
                "Insufficient evidence in the Chanakya Research Commons corpus to reliably answer this question. "
                "No retrieved papers met the relevance threshold. Try broadening your topic keywords or ingesting additional external papers from OpenAlex/arXiv."
            ),
            "citations": [],
            "retrieved_passages": [],
        }

    # Assign citation numbers [1]..[K]
    citations = []
    context_blocks = []
    for idx, psg in enumerate(top_passages, start=1):
        psg["citation_index"] = idx
        authors_str = ", ".join(psg["authors"][:2]) + (" et al." if len(psg["authors"]) > 2 else "")
        citations.append(
            {
                "index": idx,
                "paper_id": psg["paper_id"],
                "title": psg["title"],
                "authors": authors_str or "Unknown Authors",
                "year": psg["publication_year"],
                "venue": psg["venue"] or psg["primary_source"],
                "url": psg["url"],
                "doi": psg["doi"],
                "in_university_library": psg["in_university_library"],
                "save_count": psg["save_count"],
            }
        )
        context_blocks.append(
            f"[{idx}] {psg['title']} ({authors_str}, {psg['publication_year']})\nPassage: {psg['passage']}"
        )

    # Step 3: Try local Ollama LLM first; fallback to verified extractive grounded synthesis
    ollama_answer = _try_ollama_generate(q_clean, context_blocks)
    if ollama_answer:
        return {
            "question": q_clean,
            "sufficient_evidence": True,
            "generation_mode": f"ollama/{settings.OLLAMA_MODEL}",
            "answer": ollama_answer,
            "citations": citations,
            "retrieved_passages": top_passages,
        }

    # Deterministic, 100% citation-verified extractive synthesis
    lib_count = sum(1 for c in citations if c["in_university_library"])
    intro = (
        f"Based on **{len(citations)} retrieved research papers** "
        f"({lib_count} saved in the Chanakya University Library), here is the evidence-grounded summary for your query:\n\n"
    )
    bullet_lines = []
    for psg in top_passages:
        idx = psg["citation_index"]
        bullet_lines.append(
            f"- **{psg['title']}** ({psg['publication_year'] or 'n.d.'}) [{idx}]: {psg['best_sentence']}"
        )

    synthesis = (
        "\n\n**Key Takeaways:** Across the retrieved literature "
        + ", ".join(f"[{c['index']}]" for c in citations)
        + ", the passages above directly address your question with verifiable metadata and abstracts. "
        "Inspect the retrieved passages below or open any cited paper to verify methodology and full context."
    )

    return {
        "question": q_clean,
        "sufficient_evidence": True,
        "generation_mode": "extractive_grounded_synthesis",
        "answer": intro + "\n".join(bullet_lines) + synthesis,
        "citations": citations,
        "retrieved_passages": top_passages,
    }
