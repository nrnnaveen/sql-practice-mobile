"""Tests for the dual-database platform:
 - MySQL + PostgreSQL per-user sandbox databases
 - Database-specific API templates
 - Separate /editor/mysql and /editor/postgresql routes
 - get_all_user_dbs helper
"""
import pytest
from unittest.mock import patch


def _login(client, email="dualdb@example.com", password="StrongPass123!"):
    """Register and log in a user."""
    client.post("/signup", data={"email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})


# ---------------------------------------------------------------------------
# Templates API – database-specific
# ---------------------------------------------------------------------------

class TestDatabaseSpecificTemplates:
    """Tests for /api/templates?db_type=mysql|postgres."""

    def test_mysql_templates_include_ddl(self, client):
        """MySQL templates should include DDL category (CREATE TABLE)."""
        _login(client, email="tpl_mysql@example.com")
        resp = client.get("/api/templates?db_type=mysql")
        assert resp.status_code == 200
        data = resp.get_json()
        templates = data["templates"]
        assert len(templates) > 0
        # Should have DDL templates with AUTO_INCREMENT (MySQL-specific)
        all_queries = " ".join(t["query"] for t in templates)
        assert "AUTO_INCREMENT" in all_queries

    def test_postgres_templates_include_serial(self, client):
        """PostgreSQL templates should include SERIAL keyword."""
        _login(client, email="tpl_pg@example.com")
        resp = client.get("/api/templates?db_type=postgres")
        assert resp.status_code == 200
        data = resp.get_json()
        templates = data["templates"]
        assert len(templates) > 0
        all_queries = " ".join(t["query"] for t in templates)
        assert "SERIAL" in all_queries

    def test_postgres_template_alias(self, client):
        """db_type=postgresql should return PostgreSQL templates."""
        _login(client, email="tpl_pg_alias@example.com")
        resp_pg = client.get("/api/templates?db_type=postgres")
        resp_alias = client.get("/api/templates?db_type=postgresql")
        assert resp_pg.status_code == 200
        assert resp_alias.status_code == 200
        assert resp_pg.get_json() == resp_alias.get_json()

    def test_generic_templates_returned_without_db_type(self, client):
        """Calling /api/templates without db_type returns generic templates."""
        _login(client, email="tpl_generic@example.com")
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.get_json()
        templates = data["templates"]
        assert len(templates) > 0
        # Generic templates should include common ones
        names = [t["name"] for t in templates]
        assert any("SELECT" in n for n in names)

    def test_mysql_templates_category_filter(self, client):
        """Category filter works for MySQL templates."""
        _login(client, email="tpl_mysql_cat@example.com")
        resp = client.get("/api/templates?db_type=mysql&category=ddl")
        assert resp.status_code == 200
        data = resp.get_json()
        templates = data["templates"]
        assert all(t["category"] == "ddl" for t in templates)
        assert len(templates) > 0


# ---------------------------------------------------------------------------
# Editor routes
# ---------------------------------------------------------------------------

class TestEditorRoutes:
    """Tests for /editor/mysql and /editor/postgresql routes."""

    def test_editor_mysql_requires_login(self, client):
        """Unauthenticated access to /editor/mysql should redirect to login."""
        with client.session_transaction() as sess:
            sess.clear()
        resp = client.get("/editor/mysql", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/login" in resp.headers.get("Location", "")

    def test_editor_postgresql_requires_login(self, client):
        """Unauthenticated access to /editor/postgresql should redirect to login."""
        with client.session_transaction() as sess:
            sess.clear()
        resp = client.get("/editor/postgresql", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/login" in resp.headers.get("Location", "")

    def test_editor_mysql_redirects_to_dashboard_when_no_db(self, client):
        """When user has no MySQL DB, /editor/mysql redirects to dashboard."""
        _login(client, email="editor_mysql_nobd@example.com")
        with patch("app.routes.editor.get_user_db_info", return_value=None):
            resp = client.get("/editor/mysql", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/dashboard" in resp.headers.get("Location", "")

    def test_editor_postgresql_redirects_to_dashboard_when_no_db(self, client):
        """When user has no PostgreSQL DB, /editor/postgresql redirects to dashboard."""
        _login(client, email="editor_pg_nobd@example.com")
        with patch("app.routes.editor.get_user_db_info", return_value=None):
            resp = client.get("/editor/postgresql", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/dashboard" in resp.headers.get("Location", "")

    def test_editor_mysql_renders_when_db_exists(self, client):
        """When user has MySQL DB, /editor/mysql renders the editor page."""
        _login(client, email="editor_mysql_ok@example.com")
        fake_mysql_db = {
            "db_type": "mysql",
            "db_name": "sandbox_mysqluser",
            "db_user": "mysqluser",
            "db_host": "localhost",
            "db_port": 3306,
            "db_password": "pw",
        }
        with patch("app.routes.editor.get_user_db_info", return_value=fake_mysql_db):
            resp = client.get("/editor/mysql")
        assert resp.status_code == 200
        assert b"sandbox_mysqluser" in resp.data

    def test_editor_postgresql_renders_when_db_exists(self, client):
        """When user has PostgreSQL DB, /editor/postgresql renders the editor page."""
        _login(client, email="editor_pg_ok@example.com")
        fake_pg_db = {
            "db_type": "postgres",
            "db_name": "sandbox_pguser",
            "db_user": "pguser",
            "db_host": "localhost",
            "db_port": 5432,
            "db_password": "pw",
        }
        with patch("app.routes.editor.get_user_db_info", return_value=fake_pg_db):
            resp = client.get("/editor/postgresql")
        assert resp.status_code == 200
        assert b"sandbox_pguser" in resp.data


# ---------------------------------------------------------------------------
# get_all_user_dbs service helper
# ---------------------------------------------------------------------------

class TestGetAllUserDbs:
    """Tests for the get_all_user_dbs service function."""

    def test_returns_both_keys(self):
        """Return dict always has 'mysql' and 'postgres' keys."""
        from app.services.db_admin_service import get_all_user_dbs
        with patch(
            "app.services.db_admin_service.get_user_db_info", return_value=None
        ):
            result = get_all_user_dbs(999)
        assert "mysql" in result
        assert "postgres" in result

    def test_returns_correct_info_per_type(self):
        """Each key in the result corresponds to the right DB type info."""
        from app.services.db_admin_service import get_all_user_dbs

        fake_mysql = {"db_type": "mysql", "db_name": "sandbox_m"}
        fake_pg    = {"db_type": "postgres", "db_name": "sandbox_p"}

        def _fake_get(user_id, db_type=None):
            if db_type == "mysql":
                return fake_mysql
            if db_type == "postgres":
                return fake_pg
            return None

        with patch(
            "app.services.db_admin_service.get_user_db_info",
            side_effect=_fake_get,
        ):
            result = get_all_user_dbs(1)

        assert result["mysql"] == fake_mysql
        assert result["postgres"] == fake_pg

    def test_can_have_only_mysql(self):
        """User with only MySQL should have postgres=None."""
        from app.services.db_admin_service import get_all_user_dbs

        def _fake_get(user_id, db_type=None):
            if db_type == "mysql":
                return {"db_type": "mysql", "db_name": "sandbox_m"}
            return None

        with patch(
            "app.services.db_admin_service.get_user_db_info",
            side_effect=_fake_get,
        ):
            result = get_all_user_dbs(1)

        assert result["mysql"] is not None
        assert result["postgres"] is None
