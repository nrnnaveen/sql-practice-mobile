"""Tests for the API blueprint (bookmarks, templates, settings, health)."""
import json
import pytest


def _login(client, email="api_test@example.com", password="StrongPass123!"):
    """Helper: register and log in, returning the test client with session."""
    client.post("/signup", data={"email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"


class TestTemplatesEndpoint:
    def test_requires_login(self, client):
        with client.application.test_client() as c:
            resp = c.get("/api/templates")
            assert resp.status_code in (302, 401)

    def test_returns_templates(self, client):
        with client.application.test_client() as c:
            _login(c, "tpl_user@example.com")
            resp = c.get("/api/templates")
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert "templates" in data
            assert len(data["templates"]) > 0

    def test_filter_by_category(self, client):
        with client.application.test_client() as c:
            _login(c, "tpl_user2@example.com")
            resp = c.get("/api/templates?category=basics")
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert all(t["category"] == "basics" for t in data["templates"])


class TestBookmarksEndpoint:
    def test_list_empty_bookmarks(self, client):
        with client.application.test_client() as c:
            _login(c, "bm_user@example.com")
            resp = c.get("/api/bookmarks")
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data["bookmarks"] == []

    def test_create_bookmark(self, client):
        with client.application.test_client() as c:
            _login(c, "bm_create@example.com")
            resp = c.post(
                "/api/bookmarks",
                data=json.dumps({
                    "name": "My Query",
                    "query": "SELECT * FROM users",
                    "database_type": "mysql",
                }),
                content_type="application/json",
            )
            assert resp.status_code == 201
            data = json.loads(resp.data)
            assert data["success"] is True
            assert "id" in data

    def test_create_bookmark_missing_name(self, client):
        with client.application.test_client() as c:
            _login(c, "bm_fail@example.com")
            resp = c.post(
                "/api/bookmarks",
                data=json.dumps({"query": "SELECT 1", "database_type": "mysql"}),
                content_type="application/json",
            )
            assert resp.status_code == 400

    def test_delete_bookmark(self, client):
        with client.application.test_client() as c:
            _login(c, "bm_del@example.com")
            # Create
            create_resp = c.post(
                "/api/bookmarks",
                data=json.dumps({"name": "Del Me", "query": "SELECT 1", "database_type": "mysql"}),
                content_type="application/json",
            )
            bm_id = json.loads(create_resp.data)["id"]
            # Delete
            del_resp = c.delete(f"/api/bookmarks/{bm_id}")
            assert del_resp.status_code == 200
            assert json.loads(del_resp.data)["success"] is True

    def test_delete_nonexistent_bookmark(self, client):
        with client.application.test_client() as c:
            _login(c, "bm_del2@example.com")
            resp = c.delete("/api/bookmarks/99999")
            assert resp.status_code == 404


class TestSettingsEndpoint:
    def test_get_settings(self, client):
        with client.application.test_client() as c:
            _login(c, "settings_user@example.com")
            resp = c.get("/api/settings")
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert "settings" in data

    def test_update_theme(self, client):
        with client.application.test_client() as c:
            _login(c, "settings_theme@example.com")
            resp = c.post(
                "/api/settings",
                data=json.dumps({"theme": "light"}),
                content_type="application/json",
            )
            assert resp.status_code == 200
            # Verify persistence
            get_resp = c.get("/api/settings")
            data = json.loads(get_resp.data)
            assert data["settings"]["theme"] == "light"

    def test_invalid_theme(self, client):
        with client.application.test_client() as c:
            _login(c, "settings_bad@example.com")
            resp = c.post(
                "/api/settings",
                data=json.dumps({"theme": "rainbow"}),
                content_type="application/json",
            )
            assert resp.status_code == 400
