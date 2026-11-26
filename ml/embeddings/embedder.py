"""
Unified 384-dim Semantic Embedding Engine.
Uses sentence-transformers (all-MiniLM-L6-v2) when available, with a deterministic
TF-IDF + TruncatedSVD (LSA) 384-dim dense vector fallback persisted to disk so
semantic search, recommendations, and RAG work reliably on any Windows laptop.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import List, Optional, Sequence

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

SVD_MODEL_PATH = Path(settings.PROCESSED_DATA_DIR) / "semantic_svd_embedder.joblib"


class SemanticEmbedder:
    def __init__(self, target_dim: int = 384):
        self.target_dim = target_dim
        self.backend_name: str = "uninitialized"
        self._st_model = None
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._svd: Optional[TruncatedSVD] = None
        self._try_load_sentence_transformer()
        if self._st_model is None:
            self._try_load_saved_svd()

    def _try_load_sentence_transformer(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._st_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self.backend_name = f"sentence-transformers/{settings.EMBEDDING_MODEL}"
            logger.info("Loaded embedding model: %s", self.backend_name)
        except Exception as exc:
            self._st_model = None
            logger.info("SentenceTransformers unavailable (%s); using TF-IDF+SVD dense semantic fallback.", exc)

    def _try_load_saved_svd(self) -> None:
        if SVD_MODEL_PATH.exists():
            try:
                bundle = joblib.load(SVD_MODEL_PATH)
                self._vectorizer = bundle["vectorizer"]
                self._svd = bundle["svd"]
                self.backend_name = "tfidf-svd-384"
            except Exception as exc:
                logger.warning("Failed to load cached SVD embedder: %s", exc)

    def fit_corpus(self, texts: Sequence[str]) -> str:
        """Fit the fallback LSA semantic space on the corpus if SentenceTransformers is unavailable."""
        if self._st_model is not None:
            return self.backend_name

        clean_texts = [t if (t and t.strip()) else "research paper" for t in texts]
        self._vectorizer = TfidfVectorizer(
            max_features=12000,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
            min_df=1,
        )
        X = self._vectorizer.fit_transform(clean_texts)
        n_components = min(self.target_dim, max(2, min(X.shape[0] - 1, X.shape[1] - 1)))
        self._svd = TruncatedSVD(n_components=n_components, random_state=settings.RANDOM_SEED)
        self._svd.fit(X)
        SVD_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"vectorizer": self._vectorizer, "svd": self._svd}, SVD_MODEL_PATH)
        self.backend_name = f"tfidf-svd-{n_components}"
        return self.backend_name

    def _pad_and_normalize(self, mat: np.ndarray) -> np.ndarray:
        if mat.ndim == 1:
            mat = mat.reshape(1, -1)
        if mat.shape[1] < self.target_dim:
            pad = np.zeros((mat.shape[0], self.target_dim - mat.shape[1]), dtype=np.float32)
            mat = np.hstack([mat, pad])
        elif mat.shape[1] > self.target_dim:
            mat = mat[:, : self.target_dim]
        return normalize(mat.astype(np.float32), norm="l2", axis=1)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.target_dim), dtype=np.float32)
        clean_texts = [t if (t and t.strip()) else "research" for t in texts]

        if self._st_model is not None:
            vecs = self._st_model.encode(clean_texts, normalize_embeddings=True, show_progress_bar=False)
            return self._pad_and_normalize(np.asarray(vecs, dtype=np.float32))

        if self._vectorizer is None or self._svd is None:
            self._try_load_saved_svd()
        if self._vectorizer is None or self._svd is None:
            self.fit_corpus(clean_texts)

        X = self._vectorizer.transform(clean_texts)
        reduced = self._svd.transform(X)
        return self._pad_and_normalize(reduced)

    def encode_one(self, text: str) -> List[float]:
        return [round(float(x), 6) for x in self.encode([text])[0]]


_EMBEDDER_SINGLETON: Optional[SemanticEmbedder] = None
_EMBEDDER_LOCK = threading.Lock()
_PRELOAD_STARTED = False


def get_embedder() -> SemanticEmbedder:
    global _EMBEDDER_SINGLETON
    if _EMBEDDER_SINGLETON is None:
        with _EMBEDDER_LOCK:
            if _EMBEDDER_SINGLETON is None:
                _EMBEDDER_SINGLETON = SemanticEmbedder(target_dim=settings.EMBEDDING_DIM)
    return _EMBEDDER_SINGLETON


def get_embedder_status() -> str:
    """Return current embedding backend name without blocking on synchronous model loading."""
    if _EMBEDDER_SINGLETON is not None:
        return _EMBEDDER_SINGLETON.backend_name
    if SVD_MODEL_PATH.exists():
        return f"loading/{settings.EMBEDDING_MODEL} (fallback: tfidf-svd-{settings.EMBEDDING_DIM})"
    return f"initializing/{settings.EMBEDDING_MODEL}"


def preload_embedder_async() -> None:
    """Warm up the embedding model in a daemon thread so initial HTTP requests never block."""
    global _PRELOAD_STARTED
    if _PRELOAD_STARTED or _EMBEDDER_SINGLETON is not None:
        return
    _PRELOAD_STARTED = True

    def _worker() -> None:
        try:
            emb = get_embedder()
            logger.info("Background embedder warm-up complete: %s", emb.backend_name)
        except Exception as exc:
            logger.warning("Background embedder warm-up skipped (%s); will fallback on demand.", exc)

    t = threading.Thread(target=_worker, name="embedder-warmup", daemon=True)
    t.start()


def cosine_similarity_matrix(query_vec: np.ndarray, corpus_vecs: np.ndarray) -> np.ndarray:
    if corpus_vecs.size == 0:
        return np.array([], dtype=np.float32)
    q = np.asarray(query_vec, dtype=np.float32).reshape(-1)
    q_norm = np.linalg.norm(q)
    if q_norm > 0:
        q = q / q_norm
    c = np.asarray(corpus_vecs, dtype=np.float32)
    c_norms = np.linalg.norm(c, axis=1, keepdims=True)
    c_norms[c_norms == 0] = 1.0
    c = c / c_norms
    return c @ q
