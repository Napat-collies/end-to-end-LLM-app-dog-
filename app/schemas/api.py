"""Pydantic contracts for the app's input and output (CLI, FastAPI, eval)."""
from typing import Any, Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class Citation(BaseModel):
    n: int                      # the [n] number used in the answer
    breed: str
    section: str
    url: str


class ToolTrace(BaseModel):
    step: int
    name: str
    arguments: dict[str, Any] | str   # the raw string if it was not valid JSON
    ok: bool
    result_preview: str


StopReason = Literal["final_answer", "max_steps", "repeated_call"]


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    tool_calls: list[ToolTrace] = []
    steps: int
    stop_reason: StopReason
