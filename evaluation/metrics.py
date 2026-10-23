"""Pure metric functions (no LLM calls) - unit tested in tests/test_metrics.py."""
import re


def recall_at_k(retrieved_breeds: list[str], relevant: list[str], k: int) -> float:
    """Fraction of the relevant breeds that appear in the top-k retrieved chunks."""
    if not relevant:
        return 0.0
    top = set(retrieved_breeds[:k])
    return sum(1 for r in relevant if r in top) / len(relevant)


def reciprocal_rank(retrieved_breeds: list[str], relevant: list[str]) -> float:
    """1 / rank of the first chunk from a relevant breed (0 if none was retrieved)."""
    for rank, breed in enumerate(retrieved_breeds, start=1):
        if breed in relevant:
            return 1.0 / rank
    return 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


ABSTAIN_PHRASES = [
    "could not find", "couldn't find", "can't find", "cannot find", "not find",
    "no information", "not covered", "do not cover", "don't cover", "does not cover", "doesn't cover",
    "do not contain", "does not contain", "don't have", "do not have", "not in the documents",
    "ไม่พบ", "ไม่มีข้อมูล", "ไม่ครอบคลุม",
]


CITATION = re.compile(r"\[\d+\]")


def contains(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()


def has_value(text: str, value: str) -> bool:
    return contains(text, value) if "." in value else has_number(text, int(value))


def has_number(text: str, n: int) -> bool:
    return re.search(rf"(?<![\d.,]){n}(?![\d.,]*\d)", text) is not None


def check_answer(check: dict, answer: str, gold: dict | None) -> bool:
    """Is the final answer correct for this test item?

    gold = {"names": [...], "total": int} computed from the database at eval time.
    """
    kind = check["type"]
    if kind == "top":
        return all(contains(answer, n) for n in gold["names"])
    if kind == "count":
        return has_number(answer, gold["total"])
    if kind == "filter":
        need = min(3, len(gold["names"]))
        return sum(contains(answer, n) for n in gold["names"]) >= need
    if kind == "keywords":
        return all(any(contains(answer, alt) for alt in group) for group in check["any_of"])
    if kind == "offtopic":
        return not any(contains(answer, w) for w in check["forbidden"])
    if kind == "row_values":     # every number of each gold range must appear in the answer
        return all(has_value(answer, v) for group in gold["values"] for v in group)
    if kind == "grounded":      # an answer (not a refusal) that cites the documents
        return CITATION.search(answer) is not None and not any(contains(answer, p) for p in ABSTAIN_PHRASES)
    if kind == "abstain":
        return any(contains(answer, p) for p in ABSTAIN_PHRASES)
    raise ValueError(f"unknown check type {kind}")
