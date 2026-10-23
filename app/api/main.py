"""FastAPI layer: HTTP in, AskResponse out. No business logic lives here.

Run:  uv run uvicorn app.api.main:app --reload     then open http://127.0.0.1:8000

Status codes
  200 answer
  422 invalid request body (FastAPI + Pydantic do this automatically)
  429 the LLM proxy is rate-limiting us
  502 the LLM proxy failed or is unreachable
  503 data/index not built yet
  504 the LLM proxy timed out
"""
from pathlib import Path

import openai
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.schemas.api import AskRequest, AskResponse
from app.services.agent import run_agent
from app.services.context import get_context

app = FastAPI(title="Dog Breed Advisor", version="1.0")
STATIC = Path(__file__).parent / "static"


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
def ask(req: AskRequest) -> AskResponse:     # sync def -> FastAPI runs it in a worker thread
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
