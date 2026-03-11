"""Unit tests for app.services.query_service."""

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from app.services.query_service import execute_query, _paginate, PAGE_SIZE


# ---------------------------------------------------------------------------
# Helpers – create lightweight stub modules so tests don't need the real
# database drivers (mysql-connector-python / psycopg2) installed.
# ---------------------------------------------------------------------------

def _make_mysql_stub(return_value):
    mod = ModuleType("app.services.mysql_service")
    mod.run_mysql = MagicMock(return_value=return_value)
    return mod


def _make_postgres_stub(return_value):
    mod = ModuleType("app.services.postgres_service")
    mod.run_postgres = MagicMock(return_value=return_value)
    return mod


class TestPaginate:
    def test_empty_rows(self):
        rows, total_pages = _paginate([], 1)
        assert rows == []
        assert total_pages == 1

    def test_single_page(self):
        rows = list(range(50))
        result, total = _paginate(rows, 1)
        assert result == rows
        assert total == 1

    def test_first_page_of_many(self):
        rows = list(range(250))
        result, total = _paginate(rows, 1)
        assert len(result) == PAGE_SIZE
        assert total == 3  # 250 / 100 = 3 pages

    def test_last_page(self):
        rows = list(range(250))
        result, total = _paginate(rows, 3)
        assert len(result) == 50  # 250 - 200

    def test_page_clamped_to_bounds(self):
        rows = list(range(10))
        # Page 99 should clamp to last page
        result, total = _paginate(rows, 99)
        assert result == rows
        assert total == 1


class TestExecuteQuery:
    def test_empty_query_returns_error(self):
        result = execute_query("", "mysql")
        assert "error" in result

    def test_injection_blocked(self):
        result = execute_query("SELECT 1; DROP TABLE users", "mysql")
        assert "error" in result

    def test_unknown_db_type(self):
        result = execute_query("SELECT 1", "oracle")
        assert "error" in result

    def test_successful_mysql_select(self):
        mock_rows = [(1, "Alice"), (2, "Bob")]
        stub = _make_mysql_stub({"columns": ["id", "name"], "rows": mock_rows})
        with patch.dict(sys.modules, {"app.services.mysql_service": stub}):
            result = execute_query("SELECT * FROM employees", "mysql", use_cache=False)
        assert "error" not in result
        assert result["columns"] == ["id", "name"]
        assert result["total_rows"] == 2
        assert result["page"] == 1
        assert result["total_pages"] == 1
        assert "elapsed_ms" in result

    def test_successful_postgres_select(self):
        mock_rows = [(i,) for i in range(150)]
        stub = _make_postgres_stub({"columns": ["x"], "rows": mock_rows})
        with patch.dict(sys.modules, {"app.services.postgres_service": stub}):
            result = execute_query("SELECT x FROM t", "postgres", page=1, use_cache=False)
        assert result["total_rows"] == 150
        assert len(result["rows"]) == PAGE_SIZE
        assert result["total_pages"] == 2

    def test_pagination_page_2(self):
        mock_rows = [(i,) for i in range(150)]
        stub = _make_postgres_stub({"columns": ["x"], "rows": mock_rows})
        with patch.dict(sys.modules, {"app.services.postgres_service": stub}):
            result = execute_query("SELECT x FROM t", "postgres", page=2, use_cache=False)
        assert result["page"] == 2
        assert len(result["rows"]) == 50  # 150 - 100

    def test_cache_hit(self):
        mock_result = {
            "columns": ["id"],
            "rows": [(1,)],
            "_all_rows": [(1,)],
            "total_rows": 1,
            "total_pages": 1,
            "page": 1,
            "elapsed_ms": 5,
            "cached": False,
        }
        cache_key = f"mysql:{hash('SELECT 1')}"
        with patch("app.services.query_service.cache_get", return_value=mock_result) as mock_get:
            result = execute_query("SELECT 1", "mysql", use_cache=True)
        mock_get.assert_called_once_with(cache_key)
        assert result["cached"] is True

    def test_non_select_not_cached(self):
        mock_result = {"message": "Query executed successfully"}
        stub = _make_mysql_stub(mock_result)
        with (
            patch.dict(sys.modules, {"app.services.mysql_service": stub}),
            patch("app.services.query_service.cache_set") as mock_set,
        ):
            result = execute_query("INSERT INTO t VALUES (1)", "mysql", use_cache=True)
        mock_set.assert_not_called()
        assert result["message"] == "Query executed successfully"
