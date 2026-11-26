"""
Entity Resolution & Near-Duplicate Paper Detection (F5).
Combines:
  1. Exact canonical DOI matching
  2. Exact canonical arXiv ID matching
  3. Normalized title & author-variant matching (e.g., "A. Sharma" vs "Ananya Sharma")
  4. MinHash + Locality-Sensitive Hashing (datasketch) over title/abstract shingles
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Sequence, Tuple

from datasketch import MinHash, MinHashLSH


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = d.strip().rstrip(".")
    return d or None


def normalize_arxiv_id(arxiv_id: Optional[str]) -> Optional[str]:
    if not arxiv_id:
        return None
    a = arxiv_id.strip().lower()
    a = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", a)
    a = re.sub(r"\.pdf$", "", a)
    a = re.sub(r"v\d+$", "", a)
    return a.strip() or None


def normalize_title(title: str) -> str:
    if not title:
        return ""
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_author_name(name: str) -> Tuple[str, str]:
    """Return (first_initial, last_name) for robust author-variant resolution."""
    clean = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-zA-Z\s,.-]", " ", clean).strip().lower()
    if not clean:
        return ("", "")
    if "," in clean:
        parts = [p.strip() for p in clean.split(",") if p.strip()]
        last = parts[0] if parts else ""
        first_tokens = parts[1].split() if len(parts) > 1 else []
        first_init = first_tokens[0][0] if first_tokens else ""
        return (first_init, last)
    tokens = [t.strip(".") for t in clean.split() if t.strip(".")]
    if not tokens:
        return ("", "")
    if len(tokens) == 1:
        return ("", tokens[0])
    return (tokens[0][0], tokens[-1])


def normalize_authors_list(authors: Sequence[str]) -> List[str]:
    out = []
    for a in authors or []:
        fi, last = normalize_author_name(a)
        if last:
            out.append(f"{fi}.{last}" if fi else last)
    return sorted(set(out))


def author_overlap_score(authors_a: Sequence[str], authors_b: Sequence[str]) -> float:
    set_a = set(normalize_authors_list(authors_a))
    set_b = set(normalize_authors_list(authors_b))
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    # Also allow last-name match when first initial is missing
    last_a = {x.split(".")[-1] for x in set_a}
    last_b = {x.split(".")[-1] for x in set_b}
    last_jacc = len(last_a & last_b) / max(1, len(last_a | last_b))
    return max(inter / max(1, union), 0.85 * last_jacc)


def build_shingles(text: str, k: int = 3) -> List[str]:
    norm = normalize_title(text)
    if not norm:
        return []
    tokens = norm.split()
    word_shingles = [" ".join(tokens[i : i + 2]) for i in range(max(1, len(tokens) - 1))]
    char_shingles = [norm[i : i + k] for i in range(max(1, len(norm) - k + 1))]
    return list(set(word_shingles + char_shingles))


def compute_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for sh in build_shingles(text):
        m.update(sh.encode("utf-8"))
    return m


def make_canonical_key(
    title: str,
    doi: Optional[str] = None,
    arxiv_id: Optional[str] = None,
) -> str:
    ndoi = normalize_doi(doi)
    if ndoi:
        return f"doi:{hashlib.sha256(ndoi.encode()).hexdigest()[:24]}"
    narx = normalize_arxiv_id(arxiv_id)
    if narx:
        return f"arxiv:{hashlib.sha256(narx.encode()).hexdigest()[:24]}"
    nt = normalize_title(title)
    return f"title:{hashlib.sha256(nt.encode()).hexdigest()[:24]}"


class PaperDeduplicator:
    """Detects and resolves near-duplicate scholarly paper records using DOI/arXiv + MinHash LSH + Author ER."""

    def __init__(self, lsh_threshold: float = 0.55, num_perm: int = 128):
        self.lsh_threshold = lsh_threshold
        self.num_perm = num_perm

    def is_duplicate_pair(self, rec_a: Dict[str, Any], rec_b: Dict[str, Any]) -> Tuple[bool, str, float]:
        """Return (is_duplicate, match_method, confidence_score)."""
        doi_a, doi_b = normalize_doi(rec_a.get("doi")), normalize_doi(rec_b.get("doi"))
        if doi_a and doi_b and doi_a == doi_b:
            return True, "exact_doi", 1.0

        arx_a, arx_b = normalize_arxiv_id(rec_a.get("arxiv_id")), normalize_arxiv_id(rec_b.get("arxiv_id"))
        if arx_a and arx_b and arx_a == arx_b:
            return True, "exact_arxiv_id", 1.0

        t_a = normalize_title(rec_a.get("title", ""))
        t_b = normalize_title(rec_b.get("title", ""))
        if not t_a or not t_b:
            return False, "none", 0.0

        if t_a == t_b:
            auth_sim = author_overlap_score(rec_a.get("authors", []), rec_b.get("authors", []))
            if auth_sim >= 0.3 or not rec_a.get("authors") or not rec_b.get("authors"):
                return True, "normalized_title", 0.96

        title_ratio = SequenceMatcher(None, t_a, t_b).ratio()
        auth_sim = author_overlap_score(rec_a.get("authors", []), rec_b.get("authors", []))

        # Combine title fuzzy match + author overlap
        if title_ratio >= 0.86 and (auth_sim >= 0.45 or not rec_a.get("authors") or not rec_b.get("authors")):
            return True, "fuzzy_title_author", round(0.65 * title_ratio + 0.35 * max(auth_sim, 0.5), 4)

        # MinHash Jaccard similarity over title + abstract prefix
        mh_a = compute_minhash(f"{t_a} {rec_a.get('abstract', '')[:250]}", num_perm=self.num_perm)
        mh_b = compute_minhash(f"{t_b} {rec_b.get('abstract', '')[:250]}", num_perm=self.num_perm)
        mh_jacc = mh_a.jaccard(mh_b)

        if mh_jacc >= 0.68 and title_ratio >= 0.72 and auth_sim >= 0.35:
            return True, "minhash_lsh_entity_resolution", round(0.5 * mh_jacc + 0.3 * title_ratio + 0.2 * auth_sim, 4)

        return False, "none", round(max(title_ratio, mh_jacc), 4)

    def find_duplicate_pairs(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch near-duplicate detection using exact indexes + MinHash LSH candidate blocking."""
        lsh = MinHashLSH(threshold=self.lsh_threshold, num_perm=self.num_perm)
        doi_map: Dict[str, List[int]] = {}
        arxiv_map: Dict[str, List[int]] = {}
        title_map: Dict[str, List[int]] = {}
        minhashes: Dict[int, MinHash] = {}

        for idx, rec in enumerate(records):
            ndoi = normalize_doi(rec.get("doi"))
            if ndoi:
                doi_map.setdefault(ndoi, []).append(idx)
            narx = normalize_arxiv_id(rec.get("arxiv_id"))
            if narx:
                arxiv_map.setdefault(narx, []).append(idx)
            nt = normalize_title(rec.get("title", ""))
            if nt:
                title_map.setdefault(nt, []).append(idx)
            mh = compute_minhash(f"{nt} {rec.get('abstract', '')[:250]}", num_perm=self.num_perm)
            minhashes[idx] = mh
            lsh.insert(str(idx), mh)

        candidate_pairs = set()
        for bucket in list(doi_map.values()) + list(arxiv_map.values()) + list(title_map.values()):
            if len(bucket) > 1:
                for i in range(len(bucket)):
                    for j in range(i + 1, len(bucket)):
                        candidate_pairs.add((min(bucket[i], bucket[j]), max(bucket[i], bucket[j])))

        for idx, mh in minhashes.items():
            for match_key in lsh.query(mh):
                j = int(match_key)
                if idx < j:
                    candidate_pairs.add((idx, j))

        confirmed = []
        for i, j in sorted(candidate_pairs):
            is_dup, method, score = self.is_duplicate_pair(records[i], records[j])
            if is_dup:
                confirmed.append(
                    {
                        "id_a": records[i].get("record_id", i),
                        "id_b": records[j].get("record_id", j),
                        "method": method,
                        "score": score,
                    }
                )
        return confirmed


def merge_source_lists(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    merged = []
    for item in list(existing or []) + list(incoming or []):
        key = (item.get("source"), item.get("external_id") or item.get("url"))
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged
