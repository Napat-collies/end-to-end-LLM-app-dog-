"""Guarded, read-only SQL over the breed table.

Safety layers (defence in depth):
1. The model never writes SQL - it fills QueryBreedsArgs (validated by Pydantic).
2. SQL is assembled ONLY from fixed fragments in this file; every user value is
   bound with ? placeholders (no f-strings with values -> no SQL injection).
3. The sort column comes from an allow-list dict, never from the model's text.
4. assert_read_only() rejects anything that is not a single SELECT.
5. The database is opened in read-only mode, so even a bug cannot write.
"""
import re
import sqlite3
from pathlib import Path

from app.core import config
from app.schemas.tools import QueryBreedsArgs


class ToolError(Exception):
    """An error the model can fix (bad argument). Sent back to the model as text."""


SORT_COLUMNS = {"avg_weight_kg": "avg_weight_kg", "avg_life_years": "avg_life_years", "name": "name"}
FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b", re.I)


def assert_read_only(sql: str) -> None:
    stripped = sql.strip()
    if not stripped.lower().startswith("select"):
        raise ToolError("only SELECT statements are allowed")
    if ";" in stripped:
        raise ToolError("only a single statement is allowed")
    if FORBIDDEN.search(stripped):
        raise ToolError("statement contains a forbidden keyword")


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class BreedDB:
    def __init__(self, path: Path = config.DB_PATH):
        if not path.exists():
            raise FileNotFoundError(f"No database at {path}. Run: uv run python -m scripts.build_db")
        # mode=ro -> SQLite itself refuses any write
        self.con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
        self.groups = [r[0] for r in self.con.execute(
            "SELECT DISTINCT group_name FROM breeds WHERE group_name IS NOT NULL ORDER BY 1")]

    def build_query(self, args: QueryBreedsArgs) -> tuple[str, list, str]:
        where, params = [], []
        if args.name_contains:
            where.append("name LIKE ? ESCAPE '\\'")
            params.append(f"%{_escape_like(args.name_contains.strip())}%")
        if args.group:
            match = next((g for g in self.groups if g.lower() == args.group.strip().lower()), None)
            if match is None:
                raise ToolError(f"unknown group {args.group!r}. Valid groups: {', '.join(self.groups)}")
            where.append("group_name = ?")
            params.append(match)
        ranges = [
            ("avg_weight_kg", ">=", args.min_avg_weight_kg),
            ("avg_weight_kg", "<=", args.max_avg_weight_kg),
            ("avg_life_years", ">=", args.min_avg_life_years),
            ("avg_life_years", "<=", args.max_avg_life_years),
        ]
        for column, op, value in ranges:      # column/op are constants from this file
            if value is not None:
                where.append(f"{column} {op} ?")
                params.append(value)
        if args.hypoallergenic is not None:
            where.append("hypoallergenic = ?")
            params.append(1 if args.hypoallergenic else 0)
        sort_col = SORT_COLUMNS[args.sort_by]
        if sort_col != "name":
            where.append(f"{sort_col} IS NOT NULL")   # unknown values must not win a "heaviest" query
        where_sql = " AND ".join(where) if where else "1=1"
        direction = "DESC" if args.descending else "ASC"
        select = ("SELECT name, group_name, weight_min_kg, weight_max_kg, life_min, life_max, "
                  "hypoallergenic FROM breeds")
        sql = f"{select} WHERE {where_sql} ORDER BY {sort_col} {direction}, name ASC LIMIT ?"
        count_sql = f"SELECT COUNT(*) FROM breeds WHERE {where_sql}"
        return sql, params, count_sql

    def run(self, args: QueryBreedsArgs) -> dict:
        sql, params, count_sql = self.build_query(args)
        assert_read_only(sql)
        assert_read_only(count_sql)
        total = self.con.execute(count_sql, params).fetchone()[0]
        limit = min(args.limit, config.MAX_SQL_ROWS)
        rows = self.con.execute(sql, params + [limit]).fetchall()
        order = "descending (largest first)" if args.descending else "ascending (smallest first)"
        return {
            "total_matches": total,
            "returned": len(rows),
            "sorted_by": f"{args.sort_by} {order}",
            "rows": [
                {
                    "name": r[0],
                    "group": r[1],
                    "weight_kg": _fmt_range(r[2], r[3]),
                    "life_years": _fmt_range(r[4], r[5]),
                    "hypoallergenic": bool(r[6]),
                }
                for r in rows
            ],
        }


def _fmt_range(lo, hi) -> str:
    if lo is None:
        return "unknown"
    return f"{lo:g}" if lo == hi else f"{lo:g}-{hi:g}"
