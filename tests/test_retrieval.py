import numpy as np
import pytest

from app.retrieval.bm25 import BM25
from app.retrieval.chunking import split_sections, split_words
from app.retrieval.retriever import normalize


def test_split_words_overlap():
    words = " ".join(f"w{i}" for i in range(1, 15))
    chunks = split_words(words, size=6, overlap=2)
    assert chunks[0].split() == ["w1", "w2", "w3", "w4", "w5", "w6"]
    assert chunks[1].split()[:2] == ["w5", "w6"]          # shares 2 words with the previous chunk
    assert chunks[-1].split()[-1] == "w14"                # nothing is lost at the end


def test_split_words_rejects_bad_overlap():
    with pytest.raises(ValueError):
        split_words("a b c", size=3, overlap=3)


def test_sections_skip_references():
    secs = split_sections("Intro text.\n== History ==\nOld.\n== References ==\nRef 1")
    assert [s for s, _ in secs] == ["Overview", "History"]


def test_normalize_handles_zero_vector():
    m = normalize(np.array([[0.0, 0.0], [3.0, 4.0]]))
    assert np.allclose(m[1], [0.6, 0.8]) and not np.isnan(m).any()


def test_bm25_prefers_matching_doc():
    bm = BM25(["badger hunting hound", "aloof alert japanese dog"])
    s = bm.scores("bred to hunt badgers badger")
    assert s[0] > s[1]


def test_dense_search_and_metadata(retriever):
    res = retriever.search("what did dachshunds hunt badgers", mode="dense", min_score=None)
    assert res.hits[0].chunk.breed == "Dachshund"
    assert res.hits[0].chunk.url.startswith("https://en.wikipedia.org/")


def test_min_score_floor_returns_nothing(retriever):
    res = retriever.search("sourdough bread recipe", mode="dense", min_score=0.5)
    assert res.below_floor and res.hits == []


def test_breed_filter_and_resolve(retriever):
    assert retriever.resolve_breed("shiba") == "Shiba Inu"
    assert retriever.resolve_breed("Komondor") is None
    res = retriever.search("hunting dog", breed="Shiba Inu", mode="hybrid", min_score=None)
    assert {h.chunk.breed for h in res.hits} == {"Shiba Inu"}
