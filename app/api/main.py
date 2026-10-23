"""FastAPI layer: HTTP in, AskResponse out. No business logic lives here.

Run:  uv run uvicorn app.api.main:app --reload     then open http://127.0.0.1:8000

Status codes
  200 answer
  422 invalid request body (FastAPI + Pydantic do this automatically)
  429 the LLM proxy is rate-limiting us
  502 the LLM proxy failed or is unreachable
  503 data/index not built yet
  504 the LLM proxy timed out
  401 wrong or missing access code (only when ACCESS_CODE is set, e.g. on Render)
  429 also: this server's own request budget is used up (only when deployed publicly)

Public deployment protection (both optional, set as environment variables):
  ACCESS_CODE      - if set, /api/ask requires header X-Access-Code with this value.
                     Share the app as https://<app>.onrender.com/?code=<ACCESS_CODE>
  MAX_ASKS_PER_HOUR - global budget of questions per hour (default 60) so a public
                     link cannot burn through the class proxy key.
"""
import hmac
import os
import threading
import time
from collections import deque
from pathlib import Path

import openai
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

from app.schemas.api import AskRequest, AskResponse
from app.services.agent import run_agent
from app.services.context import get_context

app = FastAPI(title="Dog Breed Advisor", version="1.0")
STATIC = Path(__file__).parent / "static"


class HourlyBudget:
    """A simple global limit: at most `limit` questions in any 60-minute window."""

    def __init__(self, limit: int):
        self.limit, self.times, self.lock = limit, deque(), threading.Lock()

    def take(self) -> bool:
        now = time.monotonic()
        with self.lock:
            while self.times and now - self.times[0] > 3600:
                self.times.popleft()
            if len(self.times) >= self.limit:
                return False
            self.times.append(now)
            return True


BUDGET = HourlyBudget(int(os.environ.get("MAX_ASKS_PER_HOUR", "60")))


def check_access(code: str | None) -> None:
    expected = os.environ.get("ACCESS_CODE", "")
    if expected and not hmac.compare_digest((code or "").encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Access code missing or wrong. Open the link you were given.")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    try:
        ctx = get_context()
    except FileNotFoundError as e:
        return {"status": "not_ready", "detail": str(e)}
    return {"status": "ok", "documents": len(ctx.retriever.breeds), "chunks": len(ctx.retriever.chunks),
            "groups": len(ctx.db.groups)}


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest, x_access_code: str | None = Header(default=None)) -> AskResponse:
    # sync def -> FastAPI runs it in a worker thread
    check_access(x_access_code)
    if not BUDGET.take():
        raise HTTPException(status_code=429, detail="This demo has reached its hourly question limit. Try later.")
    try:
        ctx = get_context()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        return run_agent(req.question, ctx)
    except openai.APITimeoutError as e:
        raise HTTPException(status_code=504, detail="The language model timed out. Try again.") from e
    except openai.RateLimitError as e:
        raise HTTPException(status_code=429, detail="The language model is busy. Try again shortly.") from e
    except (openai.APIConnectionError, openai.APIStatusError) as e:
        raise HTTPException(status_code=502, detail="The language model service failed.") from e
