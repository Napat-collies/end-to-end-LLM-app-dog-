"""Build the shared ToolContext (index + database) once per process."""
from functools import lru_cache

from app.retrieval.embedding_cache import EmbeddingCache
from app.retrieval.retriever import Retriever
from app.tools.query_breeds import BreedDB
from app.tools.registry import ToolContext


@lru_cache(maxsize=1)
def get_context() -> ToolContext:
    cache = EmbeddingCache()
    return ToolContext(retriever=Retriever.load(embedder=cache.embed), db=BreedDB())
