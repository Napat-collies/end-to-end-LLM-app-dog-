import json
import sqlite3

import pytest

from app.schemas.tools import QueryBreedsArgs
from app.tools.query_breeds import ToolError, assert_read_only
from app.tools.registry import dispatch


def test_heaviest_breed(db):
    res = db.run(QueryBreedsArgs(sort_by="avg_weight_kg", descending=True, limit=1))
    assert res["rows"][0]["name"] == "Great Dane"


def test_unknown_values_never_win_a_sort(db):
    res = db.run(QueryBreedsArgs(sort_by="avg_life_years", descending=False, limit=10))
    assert "Mystery Dog" not in [r["name"] for r in res["rows"]]


def test_count_and_filters(db):
    res = db.run(QueryBreedsArgs(group="toy group"))          # case-insensitive group match
    assert res["total_matches"] == 2
    res = db.run(QueryBreedsArgs(hypoallergenic=True, max_avg_weight_kg=5))
    assert [r["name"] for r in res["rows"]] == ["Toy Poodle"]


def test_injection_in_value_is_just_data(db):
    res = db.run(QueryBreedsArgs(name_contains="x'; DROP TABLE breeds; --"))
    assert res["total_matches"] == 0
    assert db.run(QueryBreedsArgs())["total_matches"] == 5   # table still there


def test_database_is_read_only(db):
    with pytest.raises(sqlite3.OperationalError):
        db.con.execute("DELETE FROM breeds")


@pytest.mark.parametrize("sql", ["DELETE FROM breeds", "SELECT 1; DROP TABLE breeds", "PRAGMA table_info(breeds)",
                                 "SELECT * FROM breeds WHERE name = 'x' UNION SELECT sql FROM sqlite_master ATTACH"])
def test_read_only_guard(sql):
    with pytest.raises(ToolError):
        assert_read_only(sql)


def test_unknown_group_is_a_fixable_error(db):
    with pytest.raises(ToolError, match="Valid groups"):
        db.run(QueryBreedsArgs(group="Sofa Group"))


def test_dispatch_never_raises(ctx):
    ok, msg, _ = dispatch("rm_rf", "{}", ctx)
    assert not ok and "unknown tool" in msg
    ok, msg, _ = dispatch("query_breeds", "{not json", ctx)
    assert not ok and "not valid JSON" in msg
    ok, msg, _ = dispatch("query_breeds", '{"limit": 500}', ctx)
    assert not ok and "limit" in msg
    ok, msg, _ = dispatch("query_breeds", '{"sort_by": "description; DROP"}', ctx)
    assert not ok and "sort_by" in msg
    ok, msg, _ = dispatch("query_breeds", '{"extra_field": 1}', ctx)
    assert not ok


def test_dispatch_ignores_nulls(ctx):
    ok, msg, args = dispatch("query_breeds", '{"group": null, "limit": 2}', ctx)
    assert ok and json.loads(msg)["returned"] == 2 and args == {"limit": 2}


def test_search_tool_numbers_citations(ctx):
    ok, msg, _ = dispatch("search_breed_docs", '{"query": "badger hunting dachshund"}', ctx)
    assert ok and msg.startswith("[1]")
    assert ctx.citations.items[0].breed in {"Dachshund", "Shiba Inu"}


def test_search_tool_unknown_breed(ctx):
    ok, msg, _ = dispatch("search_breed_docs", '{"query": "temperament", "breed": "Komondor"}', ctx)
    assert not ok and "not in the document collection" in msg
