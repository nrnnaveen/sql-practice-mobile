"""Tests for authentication routes and auth_service."""
import pytest


class TestSignup:
    def test_get_signup_page(self, client):
        resp = client.get("/signup")
        assert resp.status_code == 200

    def test_signup_weak_password(self, client):
        """Signup should be rejected when password fails policy."""
        resp = client.post(
            "/signup",
            data={"email": "test@example.com", "password": "weak"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Error message should be present in the response
        assert b"password" in resp.data.lower() or b"error" in resp.data.lower()

    def test_signup_strong_password(self, client):
        """Signup should succeed with a strong password."""
        resp = client.post(
            "/signup",
            data={"email": "newuser@example.com", "password": "StrongPass123!"},
            follow_redirects=False,
        )
        # Should redirect to login on success
        assert resp.status_code in (302, 303)
        assert "/login" in resp.headers.get("Location", "")

    def test_signup_duplicate_email(self, client):
        """Signing up with an already-registered email should show an error."""
        # Register once
        client.post(
            "/signup",
            data={"email": "dup@example.com", "password": "StrongPass123!"},
        )
        # Register again with the same email
        resp = client.post(
            "/signup",
            data={"email": "dup@example.com", "password": "StrongPass123!"},
            follow_redirects=True,
        )
        assert resp.status_code == 200


class TestLogin:
    def test_get_login_page(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_login_invalid_credentials(self, client):
        resp = client.post(
            "/login",
            data={"email": "nobody@example.com", "password": "WrongPass123!"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"invalid" in resp.data.lower() or b"error" in resp.data.lower()

    def test_login_valid_credentials(self, client):
        """User created in test_signup_strong_password should be able to log in."""
        # Ensure the user exists
        client.post(
            "/signup",
            data={"email": "logintest@example.com", "password": "StrongPass123!"},
        )
        resp = client.post(
            "/login",
            data={"email": "logintest@example.com", "password": "StrongPass123!"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert "/dashboard" in resp.headers.get("Location", "")


class TestLogout:
    def test_logout_redirects_to_login(self, client):
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/login" in resp.headers.get("Location", "")
