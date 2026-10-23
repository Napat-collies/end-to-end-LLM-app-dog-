"""The only place in the project that talks to the class LLM proxy."""
from functools import lru_cache
from typing import Any

from openai import OpenAI

from app.core import config


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """Create the client once. Key and base URL come from the environment only."""
    return OpenAI(
        api_key=config.require_env("OPENAI_API_KEY"),
        base_url=config.require_env("OPENAI_BASE_URL"),
        timeout=config.LLM_TIMEOUT_S,
        max_retries=2,
    )


def chat(messages: list[dict[str, Any]], tools: list[dict] | None = None, client=None):
    """One chat completion at temperature 0. Returns the assistant message object."""
    client = client or get_client()
    kwargs: dict[str, Any] = {
        "model": config.CHAT_MODEL,
        "temperature": config.TEMPERATURE,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message


def embed(texts: list[str], client=None, batch_size: int = 64) -> list[list[float]]:
    """Embed many texts with bge-m3, batched. Output order == input order."""
    client = client or get_client()
    out: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        resp = client.embeddings.create(model=config.EMBED_MODEL, input=batch)
        # resp.data[i] belongs to batch[i]; never re-sort it.
        vecs = [d.embedding for d in resp.data]
        if len(vecs) != len(batch):
            raise RuntimeError(f"embedding API returned {len(vecs)} vectors for {len(batch)} inputs")
        out.extend(vecs)
    return out
