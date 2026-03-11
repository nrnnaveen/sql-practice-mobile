"""Test fixtures and application factory for pytest."""
import os
import sys
import types
import tempfile
import pytest


def _mock_db_modules():
    """Create lightweight stubs for mysql.connector and psycopg2 so the test
    suite can import the app without needing real database drivers installed."""
    # ── mysql.connector stub ──────────────────────────────────────────────
    if "mysql" not in sys.modules:
        mysql_pkg = types.ModuleType("mysql")
        mysql_connector = types.ModuleType("mysql.connector")
        mysql_connector.connect = lambda **kw: (_ for _ in ()).throw(
            Exception("No MySQL connection in tests")
        )
        mysql_pkg.connector = mysql_connector
        sys.modules["mysql"] = mysql_pkg
        sys.modules["mysql.connector"] = mysql_connector

    # ── psycopg2 stub ─────────────────────────────────────────────────────
    if "psycopg2" not in sys.modules:
        psycopg2 = types.ModuleType("psycopg2")
        psycopg2.connect = lambda **kw: (_ for _ in ()).throw(
            Exception("No PostgreSQL connection in tests")
        )
        sys.modules["psycopg2"] = psycopg2

    # ── authlib stub ──────────────────────────────────────────────────────
    if "authlib" not in sys.modules:
        authlib = types.ModuleType("authlib")
        integrations = types.ModuleType("authlib.integrations")
        flask_client = types.ModuleType("authlib.integrations.flask_client")

        class _FakeOAuth:
            def init_app(self, app): pass
            def register(self, **kw): pass

        flask_client.OAuth = _FakeOAuth
        authlib.integrations = integrations
        integrations.flask_client = flask_client
        sys.modules["authlib"] = authlib
        sys.modules["authlib.integrations"] = integrations
        sys.modules["authlib.integrations.flask_client"] = flask_client


_mock_db_modules()


# Point at a temporary database so tests don't pollute the real one
@pytest.fixture(scope="session", autouse=True)
def set_test_db(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("db")
    os.environ["DB_DIR"] = str(db_dir)


@pytest.fixture(scope="session")
def app(set_test_db):
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    yield flask_app


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()
