"""Ask one question from the terminal and see the answer, citations and tool trace.

Run:  uv run python -m scripts.ask "Which dog breeds weigh under 5 kg?"
"""
import json
import sys

from app.services.agent import run_agent
from app.services.context import get_context


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('usage: uv run python -m scripts.ask "your question"')
    question = " ".join(sys.argv[1:])
    resp = run_agent(question, get_context())
    print("\n=== Tool calls ===")
    for t in resp.tool_calls:
        status = "ok " if t.ok else "ERR"
        print(f"step {t.step} [{status}] {t.name}({json.dumps(t.arguments, ensure_ascii=False)})")
        print("        " + t.result_preview.replace("\n", " ")[:160])
    print(f"\n=== Answer ({resp.stop_reason}, {resp.steps} steps) ===")
    print(resp.answer)
    if resp.citations:
        print("\n=== Sources ===")
        for c in resp.citations:
            print(f"[{c.n}] {c.breed} - {c.section}: {c.url}")


if __name__ == "__main__":
    main()
