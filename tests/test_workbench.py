"""Tests for the new Workbench AJAX endpoints:
  - GET  /editor/get-schema
  - POST /editor/execute-query
"""
import json
import pytest


@pytest.fixture(autouse=True)
def clear_rate_limit():
    """Reset the in-process rate-limit counter before each test."""
    from app.utils.decorators import _request_log
    _request_log.clear()


def _login_fresh(app, email, password="StrongPass123!"):
    """Create a fresh test client, register and log in, return the client."""
    c = app.test_client()
    c.post("/signup", data={"email": email, "password": password})
    c.post("/login", data={"email": email, "password": password})
    return c


class TestGetSchemaEndpoint:
    """Tests for GET /editor/get-schema."""

    def test_requires_login(self, app):
        c = app.test_client()
        resp = c.get("/editor/get-schema")
        assert resp.status_code in (302, 401)

    def test_returns_json_when_no_sandbox(self, app):
        c = _login_fresh(app, "schema_user@example.com")
        resp = c.get("/editor/get-schema?db_type=mysql")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        # Without a sandbox DB, returns an empty tables list
        assert "tables" in data
        assert isinstance(data["tables"], list)

    def test_accepts_db_type_postgres(self, app):
        c = _login_fresh(app, "schema_pg_user@example.com")
        resp = c.get("/editor/get-schema?db_type=postgres")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "tables" in data


class TestExecuteQueryEndpoint:
    """Tests for POST /editor/execute-query."""

    def test_requires_login(self, app):
        c = app.test_client()
        resp = c.post(
            "/editor/execute-query",
            data={"query": "SELECT 1", "database": "mysql"},
        )
        assert resp.status_code in (302, 401)

    def test_empty_query_returns_400(self, app):
        c = _login_fresh(app, "exec_empty@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={"query": "", "database": "mysql"},
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_valid_select_returns_json_structure(self, app):
        c = _login_fresh(app, "exec_select@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={"query": "SELECT * FROM employees LIMIT 5", "database": "mysql"},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        # Must always include these keys
        assert "query_type"    in data
        assert "animation_data" in data
        assert "execution_time" in data
        assert "schema"         in data
        assert isinstance(data["schema"], list)
        assert data["query_type"] == "SELECT"

    def test_query_type_insert_detected(self, app):
        """INSERT is detected; may be blocked by validator without a sandbox DB."""
        c = _login_fresh(app, "exec_insert@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={
                "query": "INSERT INTO employees (name) VALUES ('Test')",
                "database": "mysql",
            },
        )
        data = json.loads(resp.data)
        # The query_type must be present regardless of success/failure
        assert data.get("query_type") == "INSERT"

    def test_query_type_create_detected(self, app):
        """CREATE TABLE is detected; may be blocked by validator without a sandbox DB."""
        c = _login_fresh(app, "exec_create@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={
                "query": "CREATE TABLE test_table (id INT PRIMARY KEY)",
                "database": "mysql",
            },
        )
        data = json.loads(resp.data)
        assert data.get("query_type") == "CREATE"

    def test_query_type_truncate_detected(self, app):
        """TRUNCATE is detected; may be blocked by validator without a sandbox DB."""
        c = _login_fresh(app, "exec_truncate@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={
                "query": "TRUNCATE TABLE employees",
                "database": "mysql",
            },
        )
        data = json.loads(resp.data)
        assert data.get("query_type") == "TRUNCATE"

    def test_animation_data_has_required_keys(self, app):
        c = _login_fresh(app, "exec_anim@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={"query": "SELECT 1", "database": "mysql"},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        anim = data["animation_data"]
        assert "color"       in anim
        assert "duration_ms" in anim
        assert "description" in anim
        assert "steps"       in anim

    def test_result_included_in_response(self, app):
        c = _login_fresh(app, "exec_result@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={"query": "SELECT * FROM employees", "database": "mysql"},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "result" in data

    def test_invalid_sql_returns_error_in_result(self, app):
        """Syntactically invalid SQL returns an error (in result.error or top-level)."""
        c = _login_fresh(app, "exec_invalid@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={"query": "INVALID SYNTAX $$$$", "database": "mysql"},
        )
        data = json.loads(resp.data)
        # The response must contain an error in some form:
        # - HTTP 400 with "error" key (query blocked by validator)
        # - HTTP 200 with result.error (DB execution failed)
        has_error = data.get("error") or (data.get("result") or {}).get("error")
        assert has_error, "Expected an error in the response for invalid SQL"

    def test_execution_time_is_float(self, app):
        c = _login_fresh(app, "exec_time@example.com")
        resp = c.post(
            "/editor/execute-query",
            data={"query": "SELECT 1", "database": "mysql"},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data.get("execution_time"), float)

