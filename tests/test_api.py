"""API protection for a public deployment: access code and hourly budget."""
from fastapi.testclient import TestClient

from app.api import main


def test_access_code_required_when_set(monkeypatch):
    monkeypatch.setenv("ACCESS_CODE", "secret123")
    client = TestClient(main.app)
    r = client.post("/api/ask", json={"question": "hello dog"})
    assert r.status_code == 401
    r = client.post("/api/ask", json={"question": "hello dog"}, headers={"X-Access-Code": "wrong"})
    assert r.status_code == 401


def test_budget_blocks_after_limit():
    budget = main.HourlyBudget(2)
    assert budget.take() and budget.take() and not budget.take()


def test_index_page_served():
    assert TestClient(main.app).get("/").status_code == 200
