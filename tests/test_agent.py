from app.services.agent import run_agent
from tests.conftest import FakeClient, message, tool_call


def test_happy_path_with_citation(ctx):
    client = FakeClient([
        message(tool_calls=[tool_call("c1", "search_breed_docs", '{"query": "dachshund badger"}')]),
        message("Dachshunds were bred to hunt badgers [1]."),
    ])
    resp = run_agent("What did dachshunds hunt?", ctx, client=client)
    assert resp.stop_reason == "final_answer" and resp.steps == 2
    assert [c.n for c in resp.citations] == [1]
    # message protocol: assistant(tool_calls) then tool(tool_call_id)
    second = client.requests[1]["messages"]
    assert second[2]["role"] == "assistant" and second[2]["tool_calls"][0]["id"] == "c1"
    assert second[3]["role"] == "tool" and second[3]["tool_call_id"] == "c1"
    assert "untrusted data" in second[3]["content"]
    assert client.requests[0]["temperature"] == 0


def test_error_is_fed_back_and_model_recovers(ctx):
    client = FakeClient([
        message(tool_calls=[tool_call("c1", "query_breeds", '{"limit": 999}')]),
        message(tool_calls=[tool_call("c2", "query_breeds", '{"limit": 1, "sort_by": "avg_weight_kg", "descending": true}')]),
        message("The heaviest breed is the Great Dane."),
    ])
    resp = run_agent("heaviest?", ctx, client=client)
    assert [t.ok for t in resp.tool_calls] == [False, True]
    assert "ERROR" in client.requests[1]["messages"][-1]["content"]
    assert resp.stop_reason == "final_answer"


def test_max_steps_forces_final_answer_without_tools(ctx):
    looping = [message(tool_calls=[tool_call(f"c{i}", "query_breeds", f'{{"limit": {i}}}')]) for i in range(1, 4)]
    client = FakeClient(looping + [message("Final answer.")])
    resp = run_agent("loop forever", ctx, client=client, max_steps=3)
    assert resp.stop_reason == "max_steps" and resp.answer == "Final answer."
    assert "tools" not in client.requests[-1]          # the forced final call has tools disabled


def test_repeated_identical_calls_stop_the_loop(ctx):
    same = '{"query": "shiba temperament"}'
    client = FakeClient([
        message(tool_calls=[tool_call("c1", "search_breed_docs", same)]),
        message(tool_calls=[tool_call("c2", "search_breed_docs", same)]),
        message(tool_calls=[tool_call("c3", "search_breed_docs", same)]),
        message("Shibas are independent [1]."),
    ])
    resp = run_agent("shiba?", ctx, client=client, max_steps=5)
    assert resp.stop_reason == "repeated_call"
    assert len(client.requests) == 4


def test_offtopic_no_tools(ctx):
    client = FakeClient([message("I only answer questions about dog breeds.")])
    resp = run_agent("Capital of France?", ctx, client=client)
    assert resp.tool_calls == [] and resp.citations == []


def test_citation_numbers_reset_per_question(ctx):
    for _ in range(2):
        client = FakeClient([
            message(tool_calls=[tool_call("c1", "search_breed_docs", '{"query": "shiba japan"}')]),
            message("From Japan [1]."),
        ])
        resp = run_agent("shiba origin", ctx, client=client)
        assert [c.n for c in resp.citations] == [1]
