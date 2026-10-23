"""Embed texts with bge-m3, caching vectors on disk so re-runs cost nothing.

The cache key is sha256(model + text), so changing the chunk text or the model
automatically produces new vectors.
"""
import hashlib
import sqlite3
import threading
from pathlib import Path

import numpy as np

from app.core import config
from app.core.llm import embed


class EmbeddingCache:
    def __init__(self, path: Path = config.EMBED_CACHE, model: str = config.EMBED_MODEL):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model = model
        # check_same_thread=False + a lock: the FastAPI server calls this from worker threads
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.con.execute("CREATE TABLE IF NOT EXISTS emb (key TEXT PRIMARY KEY, vec BLOB)")

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self.model}\n{text}".encode()).hexdigest()

    def embed(self, texts: list[str], client=None) -> np.ndarray:
        """Return an (n, dim) float32 array, in the same order as `texts`."""
        with self.lock:
            return self._embed(texts, client)

    def _embed(self, texts: list[str], client=None) -> np.ndarray:
        keys = [self._key(t) for t in texts]
        found: dict[str, np.ndarray] = {}
        for i in range(0, len(keys), 500):
            part = keys[i:i + 500]
            q = f"SELECT key, vec FROM emb WHERE key IN ({','.join('?' * len(part))})"
            for k, blob in self.con.execute(q, part):
                found[k] = np.frombuffer(blob, dtype=np.float32)
        missing = [i for i, k in enumerate(keys) if k not in found]
        if missing:
            vecs = embed([texts[i] for i in missing], client=client)
            rows = []
            for i, v in zip(missing, vecs):
                arr = np.asarray(v, dtype=np.float32)
                if arr.shape[0] != config.EMBED_DIM:
                    raise RuntimeError(f"expected {config.EMBED_DIM}-dim vectors, got {arr.shape[0]}")
                found[keys[i]] = arr
                rows.append((keys[i], arr.tobytes()))
            self.con.executemany("INSERT OR REPLACE INTO emb VALUES (?, ?)", rows)
            self.con.commit()
        return np.vstack([found[k] for k in keys]) if keys else np.zeros((0, config.EMBED_DIM), np.float32)
