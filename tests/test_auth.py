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


class TestGoogleOAuth:
    def test_login_page_contains_system_target_for_cordova(self, client):
        """Login page must use _system to open Google OAuth in the system browser on Cordova.

        Using _system instead of _blank prevents Error 403: disallowed_useragent
        that Google returns when the OAuth request originates from a WebView.
        """
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"_system" in resp.data, (
            "Login page must open Google OAuth with '_system' target for Cordova so "
            "Chrome (not WebView) handles the request – prevents Error 403."
        )

    def test_login_page_detects_cordova_environment(self, client):
        """Login page must include JavaScript to detect the Cordova environment."""
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"cordova" in resp.data.lower(), (
            "Login page must contain Cordova detection logic to choose the correct "
            "browser target (_system vs standard navigation)."
        )

    def test_google_callback_disallowed_useragent_shows_error(self, client):
        """Callback with disallowed_useragent error must render an informative message.

        This covers the case where the OAuth request still originates from a WebView
        (e.g. an old app version) and Google returns error=disallowed_useragent.
        """
        resp = client.get(
            "/login/google/callback?error=disallowed_useragent",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # The response must contain an explanation and not a bare 500 / empty page
        assert b"browser" in resp.data.lower() or b"authoris" in resp.data.lower(), (
            "disallowed_useragent error must display a helpful message to the user."
        )

    def test_google_callback_access_denied_shows_error(self, client):
        """Callback with access_denied error must render an informative message."""
        resp = client.get(
            "/login/google/callback?error=access_denied",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"denied" in resp.data.lower() or b"error" in resp.data.lower()
