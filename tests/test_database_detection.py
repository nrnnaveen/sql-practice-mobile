"""Tests for smart database detection and per-user sandbox database features."""
import sqlite3
import pytest
from unittest.mock import patch, MagicMock


def _login(client, email="dbtest@example.com", password="StrongPass123!"):
    """Register and log in a user."""
    client.post("/signup", data={"email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})


class TestDashboardSmartDetection:
    """Dashboard should show different content based on whether user has a DB."""

    def test_dashboard_no_db_shows_create_form(self, client):
        """New user (no sandbox DB) should see the creation form."""
        _login(client, email="no_db@example.com")
        with patch(
            "app.routes.dashboard.get_user_db_info", return_value=None
        ):
            resp = client.get("/dashboard")
        assert resp.status_code == 200
        # Should show 'create' related content
        assert b"Create" in resp.data or b"create" in resp.data or b"sandbox" in resp.data.lower()

    def test_dashboard_with_db_shows_info(self, client):
        """User with sandbox DB should see their database info."""
        _login(client, email="has_db@example.com")
        fake_db = {
            "db_type": "mysql",
            "db_name": "sandbox_testuser",
            "db_user": "testuser",
            "db_host": "db.example.com",
            "db_port": 3306,
            "db_password": "secret123",
        }
        with patch(
            "app.routes.dashboard.get_user_db_info", return_value=fake_db
        ):
            resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert b"sandbox_testuser" in resp.data
        assert b"testuser" in resp.data

    def test_dashboard_requires_login(self, client):
        """Unauthenticated request should redirect to login."""
        with client.session_transaction() as sess:
            sess.clear()
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/login" in resp.headers.get("Location", "")


class TestCheckUsernameEndpoint:
    """Tests for /api/check-username."""

    def test_check_username_not_authenticated(self, client):
        """Should return 401 when not logged in."""
        with client.session_transaction() as sess:
            sess.clear()
        resp = client.get("/api/check-username?username=testuser&db_type=mysql")
        assert resp.status_code == 401

    def test_check_username_available(self, client):
        """Should return available=True for a free username."""
        _login(client, email="check_un@example.com")
        with patch(
            "app.routes.dashboard.is_username_available", return_value=True
        ):
            resp = client.get("/api/check-username?username=freeuser&db_type=mysql")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is True

    def test_check_username_taken(self, client):
        """Should return available=False for an existing username."""
        _login(client, email="check_un2@example.com")
        with patch(
            "app.routes.dashboard.is_username_available", return_value=False
        ):
            resp = client.get("/api/check-username?username=taken&db_type=mysql")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is False

    def test_check_username_empty(self, client):
        """Empty username should return not available."""
        _login(client, email="check_un3@example.com")
        resp = client.get("/api/check-username?db_type=mysql")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is False


class TestCreateDatabaseEndpoint:
    """Tests for POST /api/create-database."""

    def test_create_db_not_authenticated(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        resp = client.post(
            "/api/create-database",
            json={"db_type": "mysql", "username": "user1", "password": "pass1234"},
        )
        assert resp.status_code == 401

    def test_create_db_missing_fields(self, client):
        _login(client, email="create_db1@example.com")
        with patch("app.routes.dashboard.get_user_db_info", return_value=None):
            resp = client.post(
                "/api/create-database",
                json={"db_type": "mysql"},
            )
        assert resp.status_code == 400
        data = resp.get_json()
        assert not data["success"]

    def test_create_db_success(self, client):
        _login(client, email="create_db2@example.com")
        fake_info = {
            "db_type": "mysql",
            "db_name": "sandbox_newuser",
            "db_user": "newuser",
            "db_host": "localhost",
            "db_port": 3306,
        }
        with patch("app.routes.dashboard.get_user_db_info", return_value=None), \
             patch("app.routes.dashboard.create_user_database", return_value=fake_info):
            resp = client.post(
                "/api/create-database",
                json={"db_type": "mysql", "username": "newuser", "password": "Pass1234!"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"]
        assert data["db_info"]["db_name"] == "sandbox_newuser"

    def test_create_db_duplicate_rejected(self, client):
        """If user already has a DB, creation should be rejected."""
        _login(client, email="create_db3@example.com")
        existing = {
            "db_type": "mysql", "db_name": "sandbox_existing",
            "db_user": "existing", "db_host": "localhost",
            "db_port": 3306, "db_password": "pw",
        }
        with patch("app.routes.dashboard.get_user_db_info", return_value=existing):
            resp = client.post(
                "/api/create-database",
                json={"db_type": "mysql", "username": "existing", "password": "Pass1234!"},
            )
        assert resp.status_code == 409
        data = resp.get_json()
        assert not data["success"]

    def test_create_db_validation_error(self, client):
        """ValueError from service should return 400."""
        _login(client, email="create_db4@example.com")
        with patch("app.routes.dashboard.get_user_db_info", return_value=None), \
             patch(
                 "app.routes.dashboard.create_user_database",
                 side_effect=ValueError("Username taken"),
             ):
            resp = client.post(
                "/api/create-database",
                json={"db_type": "mysql", "username": "bad", "password": "Pass1234!"},
            )
        assert resp.status_code == 400
        assert not resp.get_json()["success"]
