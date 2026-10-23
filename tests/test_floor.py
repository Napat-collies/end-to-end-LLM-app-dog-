"""The min_score floor is judged on the user's question, not the agent's rewritten query."""
from app.core import config
from app.services.agent import run_agent
from app.tools.registry import dispatch
from tests.conftest import FakeClient, message


def test_short_rewrite_still_answers_when_question_is_covered(ctx, monkeypatch):
    monkeypatch.setattr(config, "MIN_SCORE", 0.3)
    ctx.question = "the dachshund is a short legged hound bred to hunt badgers"
    ok, msg, _ = dispatch("search_breed_docs", '{"query": "origin", "breed": "Dachshund"}', ctx)
    assert ok and msg.startswith("[1]")          # "origin" alone would fall below the floor


def test_uncovered_question_is_rejected_even_with_a_good_query(ctx, monkeypatch):
    monkeypatch.setattr(config, "MIN_SCORE", 0.3)
    ctx.question = "sourdough bread recipe with rye flour"
    ok, msg, _ = dispatch("search_breed_docs", '{"query": "dachshund badgers hunt"}', ctx)
    assert ok and msg.startswith("NO_RESULTS")


def test_thai_question_gets_thai_instruction(ctx):
    client = FakeClient([message("มาจากญี่ปุ่น")])
    run_agent("ชิบะมาจากไหน", ctx, client=client)
    assert "MUST be written in Thai" in client.requests[0]["messages"][0]["content"]
    client = FakeClient([message("Japan")])
    run_agent("Where is the Shiba from?", ctx, client=client)
    assert "MUST be written in Thai" not in client.requests[0]["messages"][0]["content"]
