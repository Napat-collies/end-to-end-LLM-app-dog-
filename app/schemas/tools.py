"""Pydantic contracts for tool arguments.

The model writes tool arguments as JSON. We never trust that JSON: it is parsed
and validated against these schemas before any tool runs. A validation error is
sent back to the model as a string so it can fix its own call.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SearchDocsArgs(BaseModel):
    """Arguments for search_breed_docs (RAG over Wikipedia breed articles)."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=300, description="What to look for, in English or Thai.")
    breed: str | None = Field(
        default=None,
        max_length=80,
        description="Optional: restrict the search to one breed's article.",
    )

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("query must contain at least 2 non-space characters")
        return v


SortColumn = Literal["avg_weight_kg", "avg_life_years", "name"]


class QueryBreedsArgs(BaseModel):
    """Arguments for query_breeds (guarded, read-only SQL over the breed table).

    The model never writes SQL. It fills in this filter; the tool turns it into
    a fixed SQL template with ? parameter binding.
    """

    model_config = ConfigDict(extra="forbid")

    name_contains: str | None = Field(default=None, max_length=60)
    group: str | None = Field(default=None, max_length=60, description="Breed group, e.g. 'Toy Group'.")
    min_avg_weight_kg: float | None = Field(default=None, ge=0, le=150)
    max_avg_weight_kg: float | None = Field(default=None, ge=0, le=150)
    min_avg_life_years: float | None = Field(default=None, ge=0, le=30)
    max_avg_life_years: float | None = Field(default=None, ge=0, le=30)
    hypoallergenic: bool | None = None
    sort_by: SortColumn = "name"
    descending: bool = False
    limit: int = Field(default=10, ge=1, le=20)
