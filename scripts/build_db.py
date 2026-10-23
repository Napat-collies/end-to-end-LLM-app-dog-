"""Build data/breeds.db (SQLite) from data/raw/dogapi_breeds.json.

Run:  uv run python -m scripts.build_db
"""
import json
import sqlite3
import statistics

from app.core import config

SCHEMA = """
CREATE TABLE breeds (
    name            TEXT PRIMARY KEY,
    group_name      TEXT,
    life_min        REAL, life_max        REAL,
    weight_min_kg   REAL, weight_max_kg   REAL,
    avg_weight_kg   REAL,
    avg_life_years  REAL,
    hypoallergenic  INTEGER,
    description     TEXT
);
"""


def _range(obj) -> tuple[float | None, float | None]:
    """dogapi.dog stores ranges as {"min": x, "max": y}; missing/zero means unknown."""
    if not isinstance(obj, dict):
        return None, None
    lo, hi = obj.get("min"), obj.get("max")
    lo = float(lo) if isinstance(lo, (int, float)) and lo > 0 else None
    hi = float(hi) if isinstance(hi, (int, float)) and hi > 0 else None
    if lo is None:
        lo = hi
    if hi is None:
        hi = lo
    return lo, hi


def _avg(lo, hi):
    return round((lo + hi) / 2, 2) if lo is not None and hi is not None else None


def to_row(b: dict) -> tuple:
    life_lo, life_hi = _range(b.get("life"))
    m_lo, m_hi = _range(b.get("male_weight"))
    f_lo, f_hi = _range(b.get("female_weight"))
    lows = [x for x in (m_lo, f_lo) if x is not None]
    highs = [x for x in (m_hi, f_hi) if x is not None]
    w_lo = min(lows) if lows else None
    w_hi = max(highs) if highs else None
    return (
        b["name"].strip(),
        b.get("group"),
        life_lo, life_hi,
        w_lo, w_hi,
        _avg(w_lo, w_hi),
        _avg(life_lo, life_hi),
        1 if b.get("hypoallergenic") else 0,
        (b.get("description") or "").strip(),
    )


def build(raw_path=config.DOGAPI_FILE, db_path=config.DB_PATH) -> int:
    breeds = json.loads(raw_path.read_text(encoding="utf-8"))["breeds"]
    rows = {}
    for b in breeds:
        if b.get("name"):
            row = to_row(b)
            rows[row[0]] = row          # de-duplicate by name
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO breeds VALUES (?,?,?,?,?,?,?,?,?,?)", list(rows.values()))
    con.commit()
    con.close()
    return len(rows)


def sanity_report(db_path=config.DB_PATH) -> None:
    """Print a few numbers so a human can confirm the units look like kg / years."""
    con = sqlite3.connect(db_path)
    weights = [r[0] for r in con.execute("SELECT avg_weight_kg FROM breeds WHERE avg_weight_kg IS NOT NULL")]
    print(f"breeds with weight: {len(weights)}, median avg weight: {statistics.median(weights):.1f}")
    for name in ("Chihuahua", "Beagle", "Labrador Retriever", "Great Dane"):
        r = con.execute(
            "SELECT name, avg_weight_kg, avg_life_years, group_name FROM breeds WHERE name LIKE ? LIMIT 1",
            (f"%{name}%",),
        ).fetchone()
        print(f"  {name:20s} -> {r}")
    groups = [r[0] for r in con.execute("SELECT DISTINCT group_name FROM breeds ORDER BY 1")]
    print(f"groups: {groups}")
    con.close()
    if weights and statistics.median(weights) > 45:
        print("WARNING: weights look like pounds, not kg. Check the raw data before continuing.")


if __name__ == "__main__":
    n = build()
    print(f"Wrote {n} breeds to {config.DB_PATH}")
    sanity_report()
