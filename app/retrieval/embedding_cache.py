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
from app.core.llm import TRANSIENT, embed

MAX_BATCH = 32          # at most this many texts per embedding request
MAX_BATCH_WORDS = 3000  # ...and at most this many words, so long chunks don't time out the proxy


def _batches(indices: list[int], texts: list[str]):
    """Group texts so each request stays under both limits (long chunks -> smaller batches)."""
    batch, words = [], 0
    for i in indices:
        n = len(texts[i].split())
        if batch and (len(batch) >= MAX_BATCH or words + n > MAX_BATCH_WORDS):
            yield batch
            batch, words = [], 0
        batch.append(i)
        words += n
    if batch:
        yield batch


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
        # Embed in batches and SAVE EACH BATCH right away, so a network error halfway
        # through loses at most one batch - re-running continues where it stopped.
        done = 0
        for batch in _batches(missing, texts):
            vecs = self._embed_batch([texts[i] for i in batch], client)
            rows = []
            for i, v in zip(batch, vecs):
                arr = np.asarray(v, dtype=np.float32)
                if arr.shape[0] != config.EMBED_DIM:
                    raise RuntimeError(f"expected {config.EMBED_DIM}-dim vectors, got {arr.shape[0]}")
                found[keys[i]] = arr
                rows.append((keys[i], arr.tobytes()))
            self.con.executemany("INSERT OR REPLACE INTO emb VALUES (?, ?)", rows)
            self.con.commit()
            done += len(batch)
            if len(missing) > MAX_BATCH:
                print(f"  embedded {done}/{len(missing)}", flush=True)
        return np.vstack([found[k] for k in keys]) if keys else np.zeros((0, config.EMBED_DIM), np.float32)

    def _embed_batch(self, batch: list[str], client) -> list[list[float]]:
        """If the proxy keeps failing on a batch, split it in half and try the halves."""
        try:
            return embed(batch, client=client, batch_size=len(batch))
        except TRANSIENT:
            if len(batch) == 1:
                raise
            mid = len(batch) // 2
            print(f"  batch of {len(batch)} failed - splitting into {mid} + {len(batch) - mid}", flush=True)
            return self._embed_batch(batch[:mid], client) + self._embed_batch(batch[mid:], client)
