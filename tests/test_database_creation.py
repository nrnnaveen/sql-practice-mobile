"""Tests for per-user database creation service logic."""
import pytest
from unittest.mock import patch, MagicMock

from app.utils.encryption import decrypt_password, encrypt_password


class TestEncryption:
    """Tests for Fernet encryption utilities."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted text should decrypt back to original."""
        original = "super_secret_password_123"
        token = encrypt_password(original)
        assert token != original
        assert decrypt_password(token) == original

    def test_different_calls_produce_different_tokens(self):
        """Fernet uses a random IV – two encryptions of the same text differ."""
        pw = "same_password"
        t1 = encrypt_password(pw)
        t2 = encrypt_password(pw)
        assert t1 != t2  # different nonces
        # But both decrypt correctly
        assert decrypt_password(t1) == pw
        assert decrypt_password(t2) == pw

    def test_tampered_token_raises(self):
        """A tampered token should raise ValueError."""
        token = encrypt_password("secret")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(ValueError):
            decrypt_password(tampered)


class TestDbAdminServiceValidation:
    """Unit tests for db_admin_service validation logic."""

    def test_is_username_available_invalid_format(self):
        """Names that do not match the regex should be unavailable."""
        from app.services.db_admin_service import is_username_available
        # Starts with digit
        assert not is_username_available("mysql", "1badname")
        # Too short
        assert not is_username_available("mysql", "ab")
        # Contains uppercase
        assert not is_username_available("mysql", "BadName")
        # Contains space
        assert not is_username_available("mysql", "bad name")

    def test_create_user_database_bad_db_type(self):
        """Unsupported db_type should raise ValueError."""
        from app.services.db_admin_service import create_user_database
        with pytest.raises(ValueError, match="Unsupported"):
            create_user_database(1, "oracle", "alice", "password123")

    def test_create_user_database_short_password(self):
        """Password shorter than 8 chars should raise ValueError."""
        from app.services.db_admin_service import create_user_database
        with pytest.raises(ValueError, match="password"):
            create_user_database(1, "mysql", "alice", "short")

    def test_create_user_database_bad_username(self):
        """Invalid username format should raise ValueError."""
        from app.services.db_admin_service import create_user_database
        with pytest.raises(ValueError, match="Username"):
            create_user_database(1, "mysql", "1invalid", "password123")

    def test_create_user_database_username_taken(self):
        """If username is taken, should raise ValueError."""
        from app.services.db_admin_service import create_user_database
        with patch(
            "app.services.db_admin_service.is_username_available", return_value=False
        ):
            with pytest.raises(ValueError, match="already taken"):
                create_user_database(1, "mysql", "alice", "password123")

    def test_create_user_database_success_mysql(self):
        """Happy path: should call _create_mysql_db and store credentials."""
        from app.services.db_admin_service import create_user_database
        fake_info = {"host": "localhost", "port": 3306}
        with patch(
            "app.services.db_admin_service.is_username_available", return_value=True
        ), patch(
            "app.services.db_admin_service._create_mysql_db", return_value=fake_info
        ) as mock_create, patch(
            "app.services.db_admin_service._store_credentials"
        ) as mock_store:
            result = create_user_database(1, "mysql", "alice", "password123")
        mock_create.assert_called_once_with("sandbox_alice", "alice", "password123")
        mock_store.assert_called_once()
        assert result["db_name"] == "sandbox_alice"
        assert result["db_user"] == "alice"
        assert result["db_host"] == "localhost"

    def test_get_user_db_info_no_db(self, tmp_path):
        """User without a sandbox DB should get None."""
        import os, sqlite3
        os.environ["DB_DIR"] = str(tmp_path)
        from app.utils.db_init import init_db
        init_db()

        from app.services.db_admin_service import get_user_db_info
        from app.utils.db_init import DB_PATH
        # Insert a user without any DB row
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO users (id, email, password) VALUES (999, 'nodb@x.com', '')")
        conn.commit()
        conn.close()

        result = get_user_db_info(999)
        assert result is None

    def test_get_user_db_info_with_db(self, tmp_path):
        """User with a sandbox DB should return decryptable credentials."""
        import os, sqlite3
        os.environ["DB_DIR"] = str(tmp_path)
        from app.utils.db_init import init_db
        init_db()

        from app.utils.encryption import encrypt_password
        from app.services.db_admin_service import get_user_db_info
        from app.utils.db_init import DB_PATH

        enc_pw = encrypt_password("mypassword")
        conn = sqlite3.connect(DB_PATH)
        # Insert a user first (FK constraint)
        conn.execute("INSERT INTO users (id, email, password) VALUES (998, 'hasdb@x.com', '')")
        # Insert into the new user_databases table
        conn.execute(
            "INSERT INTO user_databases (user_id, db_type, db_name, db_user, db_password, db_host, db_port) "
            "VALUES (998, 'mysql', 'sandbox_foo', 'foo', ?, 'localhost', 3306)",
            (enc_pw,),
        )
        conn.commit()
        conn.close()

        result = get_user_db_info(998)
        assert result is not None
        assert result["db_name"] == "sandbox_foo"
        assert result["db_password"] == "mypassword"
