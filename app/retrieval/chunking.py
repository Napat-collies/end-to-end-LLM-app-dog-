"""Turn Wikipedia plain text into overlapping, metadata-tagged chunks."""
import json
import re
from pathlib import Path

from app.core import config
from app.schemas.docs import Chunk

HEADING = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")
SKIP_SECTIONS = {
    "see also", "references", "notes", "further reading", "external links",
    "bibliography", "sources", "citations", "footnotes", "gallery",
}


def split_words(text: str, size: int, overlap: int) -> list[str]:
    """Fixed-size word windows that share `overlap` words with the previous window."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("need size > 0 and 0 <= overlap < size")
    words = text.split()
    step = size - overlap
    out = []
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        if piece:
            out.append(" ".join(piece))
        if start + size >= len(words):
            break
    return out


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split on '== Heading ==' lines. The text before the first heading is 'Overview'."""
    sections: list[tuple[str, list[str]]] = [("Overview", [])]
    for line in text.splitlines():
        m = HEADING.match(line.strip())
        if m:
            sections.append((m.group(2), []))
        else:
            sections[-1][1].append(line)
    result = []
    for name, lines in sections:
        body = "\n".join(lines).strip()
        if body and name.lower() not in SKIP_SECTIONS:
            result.append((name, body))
    return result


def chunk_article(record: dict, size: int, overlap: int) -> list[Chunk]:
    breed = record["breed"]
    slug = re.sub(r"[^a-z0-9]+", "-", breed.lower()).strip("-")
    chunks = []
    for section, body in split_sections(record["text"]):
        for piece in split_words(body, size, overlap):
            chunks.append(Chunk(
                id=f"{slug}#{len(chunks)}",
                breed=breed,
                section=section,
                url=record["url"],
                # The header gives every chunk its context ("it" -> which breed?).
                text=f"Breed: {breed} | Section: {section}\n{piece}",
            ))
    return chunks


def load_corpus(wiki_dir: Path = config.WIKI_DIR) -> list[dict]:
    files = sorted(wiki_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No articles in {wiki_dir}. Run: uv run python -m scripts.fetch_data")
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def chunk_corpus(records: list[dict], size: int = config.CHUNK_SIZE_WORDS,
                 overlap: int = config.CHUNK_OVERLAP_WORDS) -> list[Chunk]:
    out: list[Chunk] = []
    for rec in records:
        out.extend(chunk_article(rec, size, overlap))
    return out
