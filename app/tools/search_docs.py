"""RAG tool: search the Wikipedia breed articles and return numbered passages."""
from app.core import config
from app.retrieval.retriever import Retriever
from app.schemas.api import Citation
from app.schemas.tools import SearchDocsArgs
from app.tools.query_breeds import ToolError

NOT_FOUND = ("NO_RESULTS: the breed documents do not contain information relevant to this query. "
             "Do not guess - tell the user the documents do not cover it.")


class CitationRegistry:
    """Gives every retrieved passage a stable [n] number for the whole conversation."""

    def __init__(self):
        self.items: list[Citation] = []
        self._by_chunk: dict[str, int] = {}

    def number_for(self, chunk) -> int:
        if chunk.id not in self._by_chunk:
            n = len(self.items) + 1
            self._by_chunk[chunk.id] = n
            self.items.append(Citation(n=n, breed=chunk.breed, section=chunk.section, url=chunk.url))
        return self._by_chunk[chunk.id]


def is_covered(question: str, retriever: Retriever) -> tuple[bool, float]:
    """Does the corpus cover the USER'S question? (best dense cosine >= MIN_SCORE)

    The floor is judged on the user's own question, not on the agent's rewritten
    query: a short rewrite like "origin" scores 0.37 even when the article clearly
    answers the question (the full question scores 0.54-0.64). This is also exactly
    what the min_score sweep in evaluation/eval_retrieval.py measures.
    """
    best = retriever.search(question, k=1, mode="dense", min_score=None).best_dense_score
    return (best is not None and best >= config.MIN_SCORE), (best or 0.0)


def search_breed_docs(args: SearchDocsArgs, retriever: Retriever, citations: CitationRegistry,
                      question: str | None = None) -> str:
    breed = None
    if args.breed:
        breed = retriever.resolve_breed(args.breed)
        if breed is None:
            raise ToolError(
                f"breed {args.breed!r} is not in the document collection. "
                "Search again without the breed filter, or tell the user it is not covered. "
                f"Covered breeds: {', '.join(retriever.breeds)}"
            )
    # read settings at call time so a tuned config value is always used
    if question:
        covered, _ = is_covered(question, retriever)
        if not covered:
            return NOT_FOUND
        floor = None          # already decided on the user's question
    else:
        floor = config.MIN_SCORE
    result = retriever.search(args.query, k=config.TOP_K, breed=breed,
                              mode=config.RETRIEVER, min_score=floor)
    if result.below_floor or not result.hits:
        return NOT_FOUND
    parts = []
    for hit in result.hits:
        n = citations.number_for(hit.chunk)
        body = hit.chunk.text.split("\n", 1)[-1]
        parts.append(f"[{n}] ({hit.chunk.breed} - {hit.chunk.section})\n{body}")
    return "\n\n".join(parts)
