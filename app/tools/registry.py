"""Tool specs shown to the model + the allow-listed dispatcher that runs them.

dispatch() never raises: every failure becomes an "ERROR: ..." string that is
fed back to the model, so it can correct its own call on the next step.
"""
import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from app.retrieval.retriever import Retriever
from app.schemas.tools import QueryBreedsArgs, SearchDocsArgs
from app.tools.query_breeds import BreedDB, ToolError
from app.tools.search_docs import CitationRegistry, search_breed_docs


@dataclass
class ToolContext:
    retriever: Retriever
    db: BreedDB
    citations: CitationRegistry = field(default_factory=CitationRegistry)
    question: str | None = None        # the user's original question (used for the min_score floor)


def tool_specs(db: BreedDB, retriever: Retriever) -> list[dict]:
    """JSON schemas the model sees. Written by hand to stay short and clear for a small model."""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_breed_docs",
                "description": (
                    "Search Wikipedia articles about dog breeds. Use for descriptive questions: "
                    "temperament, history, origin, care, health, exercise, grooming, behaviour. "
                    "Returns numbered passages; cite them as [n]."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string",
                                  "description": "A full question in English, e.g. "
                                                 "'Where does the Shiba Inu originate from?' - not a single word."},
                        "breed": {
                            "type": "string",
                            "description": "Optional. Only search this breed's article. Covered breeds: "
                                           + ", ".join(retriever.breeds),
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_breeds",
                "description": (
                    "Filter, sort and count ~280 breeds in a database by numbers: average adult weight (kg), "
                    "average life span (years), breed group, hypoallergenic. Use for questions like "
                    "'heaviest', 'lives longest', 'under 10 kg', 'how many breeds in a group'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name_contains": {"type": "string", "description": "Part of a breed name."},
                        "group": {"type": "string", "enum": db.groups},
                        "min_avg_weight_kg": {"type": "number"},
                        "max_avg_weight_kg": {"type": "number"},
                        "min_avg_life_years": {"type": "number"},
                        "max_avg_life_years": {"type": "number"},
                        "hypoallergenic": {"type": "boolean"},
                        "sort_by": {"type": "string", "enum": ["avg_weight_kg", "avg_life_years", "name"]},
                        "descending": {"type": "boolean", "description": "true for largest first."},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                    },
                    "required": [],
                },
            },
        },
    ]


# Allow-list: the ONLY functions the model can ever trigger.
TOOLS: dict[str, tuple[type[BaseModel], Any]] = {
    "search_breed_docs": (
        SearchDocsArgs,
        lambda args, ctx: search_breed_docs(args, ctx.retriever, ctx.citations, ctx.question),
    ),
    "query_breeds": (
        QueryBreedsArgs,
        lambda args, ctx: json.dumps(ctx.db.run(args), ensure_ascii=False),
    ),
}


def parse_arguments(raw: str | None) -> dict:
    """Parse the model's argument string. Raises ToolError with a fixable message."""
    if raw is None or raw.strip() == "":
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ToolError(f"arguments are not valid JSON ({e.msg}). Send a JSON object.") from e
    if not isinstance(value, dict):
        raise ToolError("arguments must be a JSON object")
    # Small models sometimes send null for optional fields; treat null as "not given".
    return {k: v for k, v in value.items() if v is not None}


def dispatch(name: str, raw_arguments: str | None, ctx: ToolContext) -> tuple[bool, str, dict | str]:
    """Run one tool call. Returns (ok, result_text, parsed_args_or_raw_string)."""
    if name not in TOOLS:
        return False, f"ERROR: unknown tool {name!r}. Available tools: {', '.join(TOOLS)}", raw_arguments or ""
    schema, fn = TOOLS[name]
    try:
        data = parse_arguments(raw_arguments)
    except ToolError as e:
        return False, f"ERROR: {e}", raw_arguments or ""
    try:
        args = schema.model_validate(data)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(map(str, err['loc'])) or 'arguments'}: {err['msg']}" for err in e.errors())
        return False, f"ERROR: invalid arguments for {name}: {problems}", data
    try:
        return True, fn(args, ctx), data
    except ToolError as e:
        return False, f"ERROR: {e}", data
    except Exception as e:  # never let a tool crash the agent loop
        return False, f"ERROR: tool {name} failed: {type(e).__name__}", data
