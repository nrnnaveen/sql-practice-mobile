"""Tests for app/utils/validators.py"""
import pytest
from app.utils.validators import validate_query, validate_password_strength


# ── validate_query ──────────────────────────────────────────────────────────

class TestValidateQuery:
    def test_empty_query(self):
        ok, msg = validate_query("")
        assert not ok
        assert "empty" in msg.lower()

    def test_whitespace_only(self):
        ok, msg = validate_query("   \n\t  ")
        assert not ok

    def test_too_long_query(self):
        ok, msg = validate_query("SELECT 1; " * 600)
        assert not ok
        assert "length" in msg.lower()

    def test_valid_select(self):
        ok, msg = validate_query("SELECT * FROM users")
        assert ok
        assert msg == ""

    def test_valid_select_with_where(self):
        ok, msg = validate_query("SELECT id, name FROM users WHERE active = 1")
        assert ok

    def test_valid_show_tables(self):
        ok, msg = validate_query("SHOW TABLES")
        assert ok

    def test_valid_describe(self):
        ok, msg = validate_query("DESCRIBE users")
        assert ok

    def test_valid_explain(self):
        ok, msg = validate_query("EXPLAIN SELECT * FROM orders")
        assert ok

    def test_valid_with_cte(self):
        ok, msg = validate_query("WITH cte AS (SELECT 1 AS n) SELECT * FROM cte")
        assert ok

    def test_blocks_drop(self):
        ok, msg = validate_query("DROP TABLE users")
        assert not ok
        assert "DROP" in msg

    def test_blocks_delete(self):
        ok, msg = validate_query("DELETE FROM users WHERE id = 1")
        assert not ok
        assert "DELETE" in msg

    def test_blocks_truncate(self):
        ok, msg = validate_query("TRUNCATE TABLE orders")
        assert not ok
        assert "TRUNCATE" in msg

    def test_blocks_alter(self):
        ok, msg = validate_query("ALTER TABLE users ADD COLUMN x INT")
        assert not ok
        assert "ALTER" in msg

    def test_blocks_insert(self):
        ok, msg = validate_query("INSERT INTO users VALUES (1, 'x')")
        assert not ok
        assert "INSERT" in msg

    def test_blocks_update(self):
        ok, msg = validate_query("UPDATE users SET name='x' WHERE id=1")
        assert not ok
        assert "UPDATE" in msg

    def test_blocks_grant(self):
        ok, msg = validate_query("GRANT ALL PRIVILEGES ON *.* TO 'user'@'host'")
        assert not ok

    def test_comment_bypass_attempt(self):
        """Ensure stripping comments prevents keyword bypass."""
        ok, msg = validate_query("SELECT 1; /* DROP TABLE users */")
        # After stripping, only "SELECT 1;" remains — should pass
        assert ok

    def test_line_comment_bypass(self):
        ok, msg = validate_query("SELECT 1 -- DROP TABLE users")
        assert ok

    def test_case_insensitive_block(self):
        ok, msg = validate_query("drop table users")
        assert not ok

    def test_unknown_first_token(self):
        ok, msg = validate_query("EXEC xp_cmdshell('ls')")
        assert not ok


# ── validate_password_strength ──────────────────────────────────────────────

class TestValidatePasswordStrength:
    def test_too_short(self):
        ok, msg = validate_password_strength("Short1!")
        assert not ok
        assert "12" in msg

    def test_no_uppercase(self):
        ok, msg = validate_password_strength("alllowercase1!")
        assert not ok
        assert "uppercase" in msg.lower()

    def test_no_lowercase(self):
        ok, msg = validate_password_strength("ALLUPPERCASE1!")
        assert not ok
        assert "lowercase" in msg.lower()

    def test_no_digit(self):
        ok, msg = validate_password_strength("NoDigitsHere!!")
        assert not ok
        assert "digit" in msg.lower()

    def test_no_special(self):
        ok, msg = validate_password_strength("NoSpecialChar1")
        assert not ok
        assert "special" in msg.lower()

    def test_valid_password(self):
        ok, msg = validate_password_strength("Short1!")
        assert not ok  # 7 chars – too short
        ok, msg = validate_password_strength("SecurePass123!")
        assert ok
        assert msg == ""

    def test_exactly_12_chars_valid(self):
        ok, msg = validate_password_strength("Abcdefgh12!@")
        assert ok
