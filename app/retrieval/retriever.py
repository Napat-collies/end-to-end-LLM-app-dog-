"""Vector store + retrievers (dense, BM25 baseline, hybrid) with a min_score floor.

The corpus is ~1-2k chunks, so a brute-force numpy scan takes milliseconds
(Lecture 5: an ANN index only pays off past ~10k-100k vectors).
"""
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core import config
from app.retrieval.bm25 import BM25
from app.schemas.docs import Chunk, Hit

Embedder = Callable[[list[str]], np.ndarray]


def normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0          # guard zero vectors (empty chunk) against division by zero
    return m / norms


@dataclass
class SearchResult:
    hits: list[Hit]
    best_dense_score: float | None   # None when dense scores were not computed (pure BM25)
    below_floor: bool                # True -> "not found in the documents"


class Retriever:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, embedder: Embedder):
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors are misaligned")
        self.chunks = chunks
        self.vectors = normalize(np.asarray(vectors, dtype=np.float32))
        self.embedder = embedder
        self.bm25 = BM25([c.text for c in chunks])
        self.breeds = sorted({c.breed for c in chunks})

    # ---- persistence -------------------------------------------------------
    def save(self, index_dir: Path, meta: dict) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        with open(index_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(c.model_dump_json() + "\n")
        np.save(index_dir / "vectors.npy", self.vectors)
        (index_dir / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, embedder: Embedder, index_dir: Path = config.INDEX_DIR) -> "Retriever":
        path = index_dir / "chunks.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"No index at {index_dir}. Run: uv run python -m scripts.build_index")
        chunks = [Chunk.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()]
        vectors = np.load(index_dir / "vectors.npy")
        return cls(chunks, vectors, embedder)

    # ---- helpers -----------------------------------------------------------
    def resolve_breed(self, name: str | None) -> str | None:
        """Case-insensitive match of a breed name against the corpus; None if unknown."""
        if not name:
            return None
        low = name.strip().lower()
        for b in self.breeds:
            if b.lower() == low:
                return b
        for b in self.breeds:            # partial match, e.g. "husky" -> "Siberian Husky"
            if low in b.lower() or b.lower() in low:
                return b
        return None

    def _mask(self, breed: str | None) -> np.ndarray:
        if breed is None:
            return np.ones(len(self.chunks), dtype=bool)
        return np.array([c.breed == breed for c in self.chunks])

    @staticmethod
    def _top(scores: np.ndarray, mask: np.ndarray, k: int) -> list[int]:
        idx = np.where(mask)[0]
        # sort by (-score, index): highest first, ties broken by lower index
        order = sorted(idx.tolist(), key=lambda i: (-scores[i], i))
        return order[:k]

    def dense_scores(self, query: str) -> np.ndarray:
        q = normalize(np.asarray(self.embedder([query]), dtype=np.float32))[0]
        return self.vectors @ q          # cosine similarity, because both sides are unit length

    # ---- search ------------------------------------------------------------
    def search(self, query: str, k: int = config.TOP_K, breed: str | None = None,
               mode: str = config.RETRIEVER, min_score: float | None = config.MIN_SCORE) -> SearchResult:
        mask = self._mask(breed)
        dense = self.dense_scores(query) if mode in ("dense", "hybrid") else None
        best = float(dense[mask].max()) if dense is not None and mask.any() else None

        if min_score is not None and best is not None and best < min_score:
            return SearchResult(hits=[], best_dense_score=best, below_floor=True)

        if mode == "dense":
            order = self._top(dense, mask, k)
            hits = [Hit(chunk=self.chunks[i], score=round(float(dense[i]), 4)) for i in order]
        elif mode == "bm25":
            bm = np.array(self.bm25.scores(query))
            order = [i for i in self._top(bm, mask, k) if bm[i] > 0]
            hits = [Hit(chunk=self.chunks[i], score=round(float(bm[i]), 4)) for i in order]
        elif mode == "hybrid":
            bm = np.array(self.bm25.scores(query))
            rrf = np.zeros(len(self.chunks))
            for scores in (dense, bm):
                for rank, i in enumerate(self._top(scores, mask, 50)):
                    if scores is dense or bm[i] > 0:
                        rrf[i] += 1.0 / (60 + rank + 1)     # Reciprocal Rank Fusion, k=60
            order = self._top(rrf, mask & (rrf > 0), k)
            hits = [Hit(chunk=self.chunks[i], score=round(float(rrf[i]), 5)) for i in order]
        else:
            raise ValueError(f"unknown retriever mode: {mode}")
        return SearchResult(hits=hits, best_dense_score=best, below_floor=False)
