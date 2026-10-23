"""End-to-end agent evaluation (agent + tools vs. a no-tools baseline).

Metrics
  * Tool-selection accuracy: the set of tools the agent called == expected set
  * SQL execution match:      the agent's query_breeds call returned the gold rows / count
                              (gold is computed by running the gold filter on the same DB)
  * Answer accuracy:          automatic check of the final answer (names, number, keywords,
                              refusal / abstention) - for both the agent and the baseline
Baseline = the same model with no tools and no retrieval (answer_without_tools).

Run:  uv run python -m evaluation.eval_agent
Writes evaluation/results/agent.md and agent.json
"""
import json
from pathlib import Path

from app.schemas.tools import QueryBreedsArgs
from app.services.agent import answer_without_tools, run_agent
from app.services.context import get_context
from evaluation.metrics import check_answer, mean

HERE = Path(__file__).parent
RESULTS = HERE / "results"
SQL_CHECKS = {"top", "count", "filter"}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def gold_for(item: dict, db) -> dict | None:
    """Run the gold filter on the database -> {"names": [...], "total": n}."""
    check = item["check"]
    if check["type"] not in SQL_CHECKS:
        return None
    args = QueryBreedsArgs.model_validate({"limit": 20, **check["gold"]})
    if args.group and args.group not in db.groups:
        raise ValueError(f"{item['id']}: group {args.group!r} not in database groups {db.groups} - edit agent_set.jsonl")
    res = db.run(args)
    names = [r["name"] for r in res["rows"]]
    if check["type"] == "top":
        names = names[: check["gold"].get("limit", 1)]
    return {"names": names, "total": res["total_matches"]}


def sql_match(item: dict, trace, db, gold: dict) -> bool:
    """Did any of the agent's query_breeds calls return the gold answer?"""
    for t in trace:
        if t.name != "query_breeds" or not t.ok or not isinstance(t.arguments, dict):
            continue
        res = db.run(QueryBreedsArgs.model_validate(t.arguments))
        names = {r["name"] for r in res["rows"]}
        if item["check"]["type"] == "top" and set(gold["names"]) <= names:
            return True
        if item["check"]["type"] in ("count", "filter") and res["total_matches"] == gold["total"]:
            return True
    return False


def main() -> None:
    items = load_jsonl(HERE / "agent_set.jsonl")
    ctx = get_context()
    rows = []
    for it in items:
        gold = gold_for(it, ctx.db)
        print(f"[{it['id']}] {it['question']}")
        resp = run_agent(it["question"], ctx)
        base = answer_without_tools(it["question"])
        called = sorted({t.name for t in resp.tool_calls})
        row = {
            "id": it["id"], "lang": it["lang"], "question": it["question"], "check": it["check"]["type"],
            "gold": gold,
            "expected_tools": it["expected_tools"], "called_tools": called,
            "tool_ok": None if it["expected_tools"] is None else set(called) == set(it["expected_tools"]),
            "sql_match": sql_match(it, resp.tool_calls, ctx.db, gold) if gold else None,
            "agent_correct": check_answer(it["check"], resp.answer, gold),
            "baseline_correct": check_answer(it["check"], base, gold),
            "steps": resp.steps, "stop_reason": resp.stop_reason,
            "agent_answer": resp.answer, "baseline_answer": base,
            "trace": [t.model_dump() for t in resp.tool_calls],
        }
        rows.append(row)
        print(f"    tools={called} tool_ok={row['tool_ok']} sql={row['sql_match']} "
              f"agent={row['agent_correct']} baseline={row['baseline_correct']}")

    def rate(key, subset=rows):
        vals = [r[key] for r in subset if r[key] is not None]
        return f"{mean([1.0 if v else 0.0 for v in vals]):.2f} ({sum(vals)}/{len(vals)})" if vals else "-"

    groups = {
        "SQL questions": [r for r in rows if r["check"] in SQL_CHECKS],
        "Document questions": [r for r in rows if r["check"] == "keywords"
                               and r["expected_tools"] == ["search_breed_docs"]],
        "Both tools": [r for r in rows if r["expected_tools"] and len(r["expected_tools"]) == 2],
        "Off-topic / not covered": [r for r in rows if r["check"] in ("offtopic", "abstain")],
        "All": rows,
    }
    md = ["# Agent evaluation", "",
          f"{len(rows)} questions. Baseline = same model, no tools, no retrieval. temperature=0.", "",
          "| Subset | n | Tool selection | SQL exec match | Answer acc. (agent) | Answer acc. (baseline) |",
          "|---|---|---|---|---|---|"]
    for name, subset in groups.items():
        md.append(f"| {name} | {len(subset)} | {rate('tool_ok', subset)} | {rate('sql_match', subset)} | "
                  f"{rate('agent_correct', subset)} | {rate('baseline_correct', subset)} |")
    md += ["", f"Average agent steps: {mean([r['steps'] for r in rows]):.2f}; "
               f"stopped by guardrail: {sum(r['stop_reason'] != 'final_answer' for r in rows)}", "",
           "## Items the agent got wrong", ""]
    wrong = [r for r in rows if not r["agent_correct"] or r["tool_ok"] is False or r["sql_match"] is False]
    for r in wrong:
        md += [f"### {r['id']}: {r['question']}",
               f"- expected tools {r['expected_tools']}, called {r['called_tools']}; sql_match={r['sql_match']}",
               f"- gold: {r['gold']}",
               f"- agent answer: {r['agent_answer'][:400]!r}", ""]
    if not wrong:
        md.append("None.")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "agent.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (RESULTS / "agent.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
