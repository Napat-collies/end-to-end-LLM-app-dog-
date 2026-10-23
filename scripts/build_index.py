"""Chunk the Wikipedia articles, embed every chunk with bge-m3, save the index.

Run:  uv run python -m scripts.build_index
"""
from app.core import config
from app.retrieval.chunking import chunk_corpus, load_corpus
from app.retrieval.embedding_cache import EmbeddingCache
from app.retrieval.retriever import Retriever


def main() -> None:
    records = load_corpus()
    chunks = chunk_corpus(records, config.CHUNK_SIZE_WORDS, config.CHUNK_OVERLAP_WORDS)
    print(f"{len(records)} articles -> {len(chunks)} chunks "
          f"(size={config.CHUNK_SIZE_WORDS} words, overlap={config.CHUNK_OVERLAP_WORDS})")
    cache = EmbeddingCache()
    vectors = cache.embed([c.text for c in chunks])
    retriever = Retriever(chunks, vectors, embedder=cache.embed)
    retriever.save(config.INDEX_DIR, meta={
        "embed_model": config.EMBED_MODEL,
        "chunk_size_words": config.CHUNK_SIZE_WORDS,
        "chunk_overlap_words": config.CHUNK_OVERLAP_WORDS,
        "n_chunks": len(chunks),
    })
    print(f"Saved index to {config.INDEX_DIR}")


if __name__ == "__main__":
    main()
