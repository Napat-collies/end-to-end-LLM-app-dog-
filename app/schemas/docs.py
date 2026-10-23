"""Data shapes for the document corpus and retrieval results."""
from pydantic import BaseModel


class Chunk(BaseModel):
    id: str            # e.g. "beagle#7"
    breed: str         # e.g. "Beagle"
    section: str       # e.g. "Temperament"
    url: str           # Wikipedia URL, used for citations
    text: str          # the text that is embedded and shown to the model


class Hit(BaseModel):
    chunk: Chunk
    score: float       # higher = better (cosine for dense, BM25/RRF score otherwise)
