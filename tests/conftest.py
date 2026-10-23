"""Offline test fixtures: tiny corpus, tiny database, fake embedder, fake LLM.

No test calls the real proxy, so `uv run pytest` works without an API key.
"""
import copy
import hashlib
import json
import re
from types import SimpleNamespace

import numpy as np
import pytest

from app.core import config
from app.retrieval.chunking import chunk_corpus
from app.retrieval.retriever import Retriever
from app.tools.query_breeds import BreedDB
from app.tools.registry import ToolContext
from scripts import build_db

ARTICLES = [
    {"breed": "Shiba Inu", "url": "https://en.wikipedia.org/wiki/Shiba_Inu",
     "text": "The Shiba Inu is a breed of hunting dog from Japan.\n\n== Temperament ==\n"
             "The Shiba is independent, alert and can be aloof with strangers."},
    {"breed": "Dachshund", "url": "https://en.wikipedia.org/wiki/Dachshund",
     "text": "The dachshund is a short-legged hound bred to hunt badgers.\n\n== History ==\n"
             "Dachshunds were developed in Germany to dig into badger dens.\n\n== References ==\nignored"},
]

DOGAPI = {"breeds": [
    {"name": "Chihuahua", "group": "Toy Group", "life": {"min": 14, "max": 16},
     "male_weight": {"min": 1, "max": 3}, "female_weight": {"min": 1, "max": 3}, "hypoallergenic": False},
    {"name": "Toy Poodle", "group": "Toy Group", "life": {"min": 14, "max": 18},
     "male_weight": {"min": 2, "max": 4}, "female_weight": {"min": 2, "max": 4}, "hypoallergenic": True},
    {"name": "Great Dane", "group": "Working Group", "life": {"min": 7, "max": 10},
     "male_weight": {"min": 54, "max": 90}, "female_weight": {"min": 45, "max": 59}, "hypoallergenic": False},
    {"name": "Border Collie", "group": "Herding Group", "life": {"min": 12, "max": 15},
     "male_weight": {"min": 14, "max": 20}, "female_weight": {"min": 12, "max": 19}, "hypoallergenic": False},
    {"name": "Mystery Dog", "group": "Herding Group", "life": {}, "male_weight": {}, "female_weight": {}},
]}


def fake_embed(texts: list[str]) -> np.ndarray:
    """Deterministic bag-of-words hashed into 1024 dims - stands in for bge-m3 in tests."""
    out = np.zeros((len(texts), 1024), dtype=np.float32)
    for i, t in enumerate(texts):
        for w in re.findall(r"\w+", t.lower()):
            out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 1024] += 1.0
    return out


@pytest.fixture
def retriever():
    chunks = chunk_corpus(ARTICLES, size=20, overlap=3)
    return Retriever(chunks, fake_embed([c.text for c in chunks]), embedder=fake_embed)


@pytest.fixture
def db(tmp_path):
    raw = tmp_path / "dogapi.json"
    raw.write_text(json.dumps(DOGAPI))
    path = tmp_path / "breeds.db"
    build_db.build(raw, path)
    return BreedDB(path)


@pytest.fixture
def ctx(retriever, db, monkeypatch):
    monkeypatch.setattr(config, "MIN_SCORE", 0.05)   # fake embeddings have lower cosines than bge-m3
    return ToolContext(retriever=retriever, db=db)


def tool_call(id_, name, arguments):
    return SimpleNamespace(id=id_, type="function",
                           function=SimpleNamespace(name=name, arguments=arguments))


def message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or None)


class FakeClient:
    """Replays scripted assistant messages and records every request."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))   # snapshot: the agent keeps appending to messages
        msg = self.script.pop(0) if self.script else message("(script exhausted)")
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
