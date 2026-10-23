"""Retrieval evaluation (capability family 3).

Experiments
  1. Baseline vs proposed: BM25 (keyword baseline) vs dense bge-m3 vs hybrid (RRF),
     Recall@1/@3/@5 and MRR@10 on 32 labelled questions (22 English, 10 Thai).
  2. Chunk-size sweep: 100 / 250 / 500 words (15% overlap) -> justifies CHUNK_SIZE_WORDS.
  3. min_score sweep on 32 answerable + 10 unanswerable questions -> justifies MIN_SCORE.
     The naive default is "no floor" (always answer).

Run:  uv run python -m evaluation.eval_retrieval
Writes evaluation/results/retrieval.md and retrieval.json
"""
import json
from pathlib import Path

from app.core import config
from app.retrieval.chunking import chunk_corpus, load_corpus
from app.retrieval.embedding_cache import EmbeddingCache
from app.retrieval.retriever import Retriever
from evaluation.metrics import mean, recall_at_k, reciprocal_rank

HERE = Path(__file__).parent
RESULTS = HERE / "results"
CHUNK_SIZES = [100, 250, 500]
MODES = ["bm25", "dense", "hybrid"]
DEPTH = 10


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def breeds_ranked(retriever: Retriever, query: str, mode: str) -> list[str]:
    result = retriever.search(query, k=DEPTH, mode=mode, min_score=None)
    return [h.chunk.breed for h in result.hits]


def score_config(retriever: Retriever, items: list[dict], mode: str) -> tuple[dict, list[dict]]:
    rows = []
    for it in items:
        ranked = breeds_ranked(retriever, it["query"], mode)
        rows.append({
            "id": it["id"], "lang": it["lang"], "query": it["query"], "relevant": it["relevant"],
            "top3": ranked[:3],
            "r1": recall_at_k(ranked, it["relevant"], 1),
            "r3": recall_at_k(ranked, it["relevant"], 3),
            "r5": recall_at_k(ranked, it["relevant"], 5),
            "mrr": reciprocal_rank(ranked, it["relevant"]),
        })

    def agg(subset):
        return {m: round(mean([r[m] for r in subset]), 3) for m in ("r1", "r3", "r5", "mrr")} | {"n": len(subset)}

    summary = {
        "all": agg(rows),
        "en": agg([r for r in rows if r["lang"] == "en"]),
        "th": agg([r for r in rows if r["lang"] == "th"]),
    }
    return summary, rows


def min_score_sweep(retriever: Retriever, answerable: list[dict], unanswerable: list[dict]) -> tuple:
    def best(q):
        return retriever.search(q, k=1, mode="dense", min_score=None).best_dense_score

    a_scores = [best(it["query"]) for it in answerable]
    u_scores = [(it["kind"], best(it["query"])) for it in unanswerable]
    rows = []
    thresholds = [0.0] + [round(0.30 + 0.05 * i, 2) for i in range(9)]   # 0.0 = naive default (no floor)
    for t in thresholds:
        kept = mean([1.0 if s >= t else 0.0 for s in a_scores])
        rejected = mean([1.0 if s < t else 0.0 for _, s in u_scores])
        rej_off = mean([1.0 if s < t else 0.0 for k, s in u_scores if k == "off_topic"])
        rej_unc = mean([1.0 if s < t else 0.0 for k, s in u_scores if k == "uncovered_breed"])
        rows.append({"min_score": t, "answerable_kept": round(kept, 3), "unanswerable_rejected": round(rejected, 3),
                     "offtopic_rejected": round(rej_off, 3), "uncovered_breed_rejected": round(rej_unc, 3),
                     "balanced_accuracy": round((kept + rejected) / 2, 3)})
    return rows, a_scores, u_scores


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    answerable = load_jsonl(HERE / "retrieval_set.jsonl")
    unanswerable = load_jsonl(HERE / "unanswerable_set.jsonl")
    records = load_corpus()
    cache = EmbeddingCache()

    report = {"chunk_sweep": {}, "per_query": {}}
    md = ["# Retrieval evaluation", "",
          f"{len(answerable)} labelled questions ({sum(i['lang'] == 'en' for i in answerable)} EN, "
          f"{sum(i['lang'] == 'th' for i in answerable)} TH) over {len(records)} Wikipedia articles. "
          "A hit = a chunk from a relevant breed's article. Embeddings: bge-m3.", ""]

    retrievers = {}
    for size in CHUNK_SIZES:
        overlap = round(size * 0.15)
        chunks = chunk_corpus(records, size, overlap)
        print(f"chunk size {size}: {len(chunks)} chunks - embedding (cached after first run)...")
        vectors = cache.embed([c.text for c in chunks])
        retrievers[size] = Retriever(chunks, vectors, embedder=cache.embed)
        report["chunk_sweep"][size] = {}
        for mode in MODES:
            summary, rows = score_config(retrievers[size], answerable, mode)
            report["chunk_sweep"][size][mode] = summary
            report["per_query"][f"{size}/{mode}"] = rows

    # --- Table 1: baseline vs proposed at the configured chunk size -----------------------------
    size = config.CHUNK_SIZE_WORDS if config.CHUNK_SIZE_WORDS in retrievers else 250
    md += [f"## 1. Retriever comparison (chunk size {size} words)", ""]
    rows = []
    for mode in MODES:
        s = report["chunk_sweep"][size][mode]
        label = {"bm25": "BM25 (baseline)", "dense": "Dense bge-m3", "hybrid": "Hybrid (RRF)"}[mode]
        rows.append([label, s["all"]["r1"], s["all"]["r3"], s["all"]["r5"], s["all"]["mrr"],
                     s["en"]["r5"], s["th"]["r5"]])
    md += [md_table(["Retriever", "Recall@1", "Recall@3", "Recall@5", "MRR@10", "Recall@5 EN", "Recall@5 TH"], rows), ""]

    # --- Table 2: chunk-size sweep ------------------------------------------------------------------
    md += ["## 2. Chunk-size sweep (dense, 15% overlap)", ""]
    rows = []
    for sz in CHUNK_SIZES:
        s = report["chunk_sweep"][sz]["dense"]["all"]
        rows.append([sz, len(retrievers[sz].chunks), s["r1"], s["r3"], s["r5"], s["mrr"]])
    md += [md_table(["Chunk size (words)", "# chunks", "Recall@1", "Recall@3", "Recall@5", "MRR@10"], rows), ""]

    # --- Table 3: min_score sweep -------------------------------------------------------------------
    sweep, a_scores, u_scores = min_score_sweep(retrievers[size], answerable, unanswerable)
    report["min_score_sweep"] = sweep
    best_row = max(sweep, key=lambda r: (r["balanced_accuracy"], r["answerable_kept"]))
    md += ["## 3. min_score sweep (dense; 0.0 = naive default, no floor)", "",
           md_table(["min_score", "Answerable kept", "Unanswerable rejected", "Off-topic rejected",
                     "Uncovered breed rejected", "Balanced acc."],
                    [[r["min_score"], r["answerable_kept"], r["unanswerable_rejected"], r["offtopic_rejected"],
                      r["uncovered_breed_rejected"], r["balanced_accuracy"]] for r in sweep]), "",
           f"Best balanced accuracy: min_score = {best_row['min_score']} "
           f"(config.MIN_SCORE is currently {config.MIN_SCORE}).", "",
           f"Best-score ranges - answerable: {min(a_scores):.3f}..{max(a_scores):.3f}; "
           f"unanswerable: {min(s for _, s in u_scores):.3f}..{max(s for _, s in u_scores):.3f}", ""]
    report["score_distributions"] = {"answerable": a_scores, "unanswerable": u_scores}

    # --- Failures for the report ----------------------------------------------------------------------
    best_mode = max(MODES, key=lambda m: report["chunk_sweep"][size][m]["all"]["mrr"])
    fails = [r for r in report["per_query"][f"{size}/{best_mode}"] if r["r5"] < 1.0]
    md += [f"## 4. Failures of the best retriever ({best_mode}, Recall@5 < 1)", ""]
    if fails:
        md += [md_table(["id", "query", "relevant", "top-3 retrieved", "Recall@5"],
                        [[f["id"], f["query"], ", ".join(f["relevant"]), ", ".join(f["top3"]), f["r5"]]
                         for f in fails]), ""]
    else:
        md += ["No failures at Recall@5.", ""]

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "retrieval.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (RESULTS / "retrieval.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\nSaved {RESULTS / 'retrieval.md'}")


if __name__ == "__main__":
    main()
