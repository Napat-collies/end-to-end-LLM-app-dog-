"""All project settings live here, in one place.

Secrets (API key, proxy URL) come ONLY from the environment / .env file.
Everything else is a plain constant so the evaluation is reproducible.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # read .env into environment variables (does not override real env vars)

# --- Models (fixed by the course) -------------------------------------------
CHAT_MODEL = "gemma-4-E4B-it"
EMBED_MODEL = "bge-m3"
EMBED_DIM = 1024
TEMPERATURE = 0.0          # everything we evaluate must be repeatable
LLM_TIMEOUT_S = 60.0

# --- Paths ------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WIKI_DIR = RAW_DIR / "wiki"
DOGAPI_FILE = RAW_DIR / "dogapi_breeds.json"
BREED_LIST_FILE = DATA_DIR / "wiki_breeds.txt"
DB_PATH = DATA_DIR / "breeds.db"
INDEX_DIR = DATA_DIR / "index"
EMBED_CACHE = DATA_DIR / "cache" / "embeddings.sqlite"

# --- Retrieval settings -----------------------------------------------------
# Chosen by the chunk-size sweep in evaluation/eval_retrieval.py (see README results).
CHUNK_SIZE_WORDS = 250
CHUNK_OVERLAP_WORDS = round(CHUNK_SIZE_WORDS * 0.15)   # 15% overlap
TOP_K = 4
# Retriever used by the app: "dense" (bge-m3), "bm25", or "hybrid" (RRF of both).
# Set this to whatever wins in evaluation/eval_retrieval.py.
RETRIEVER = "dense"
# If the best dense cosine score is below this, we say "not found" instead of guessing.
# Tuned by the min_score sweep in evaluation/eval_retrieval.py.
MIN_SCORE = 0.45

# --- Agent settings ---------------------------------------------------------
MAX_STEPS = 5              # hard stop for the agent loop
MAX_SQL_ROWS = 20          # the SQL tool never returns more rows than this


def require_env(name: str) -> str:
    """Read a required environment variable or fail with a clear message."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable {name}. "
            "Copy .env.example to .env and fill in your values."
        )
    return value
