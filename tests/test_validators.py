"""Unit tests for app.utils.validators."""

import pytest

from app.utils.validators import validate_query, sanitize_identifier, MAX_QUERY_LENGTH


class TestValidateQuery:
    def test_empty_query_rejected(self):
        assert validate_query("") is not None
        assert validate_query("   ") is not None

    def test_valid_select_passes(self):
        assert validate_query("SELECT * FROM employees") is None

    def test_valid_insert_passes(self):
        assert validate_query("INSERT INTO t (a) VALUES (1)") is None

    def test_valid_update_passes(self):
        assert validate_query("UPDATE t SET a = 1 WHERE id = 2") is None

    def test_valid_ddl_passes(self):
        assert validate_query("CREATE TABLE foo (id INT PRIMARY KEY)") is None

    def test_query_too_long(self):
        long_query = "SELECT " + "a" * MAX_QUERY_LENGTH
        result = validate_query(long_query)
        assert result is not None
        assert "too long" in result.lower()

    def test_stacked_statements_rejected(self):
        evil = "SELECT 1; DROP TABLE users"
        assert validate_query(evil) is not None

    def test_exec_rejected(self):
        assert validate_query("EXEC(xp_cmdshell 'dir')") is not None

    def test_sleep_injection_rejected(self):
        assert validate_query("SELECT * FROM t WHERE id=1 OR sleep(5)") is not None

    def test_pg_sleep_injection_rejected(self):
        assert validate_query("SELECT pg_sleep(10)") is not None

    def test_load_data_rejected(self):
        assert validate_query("LOAD DATA INFILE '/etc/passwd' INTO TABLE t") is not None

    def test_outfile_rejected(self):
        assert validate_query("SELECT * INTO OUTFILE '/tmp/out.txt' FROM t") is not None

    def test_xp_cmdshell_rejected(self):
        assert validate_query("EXEC xp_cmdshell('ls')") is not None

    def test_union_null_injection_rejected(self):
        assert validate_query(
            "SELECT id FROM users WHERE id=1 UNION ALL SELECT NULL,NULL,NULL"
        ) is not None

    def test_tautology_injection_rejected(self):
        # Tautology used as injection bypass: OR '1'='1'
        assert validate_query("SELECT * FROM t WHERE id=1 OR '1'='1'") is not None

    def test_comment_injection_rejected(self):
        assert validate_query("SELECT * FROM t WHERE 1=1 -- OR 1=1") is not None

    def test_normal_comment_in_query_allowed(self):
        # A plain comment at the start is fine (no injection pattern)
        # Note: our pattern only blocks -- followed by OR/AND
        assert validate_query("-- get all employees\nSELECT * FROM employees") is None


class TestSanitizeIdentifier:
    def test_clean_name_unchanged(self):
        assert sanitize_identifier("employees") == "employees"

    def test_spaces_replaced(self):
        result = sanitize_identifier("my table")
        assert " " not in result

    def test_special_chars_replaced(self):
        result = sanitize_identifier("col; DROP TABLE users")
        assert ";" not in result
        assert "DROP" not in result or result.replace("_", "").isalnum()

    def test_length_capped(self):
        long_name = "a" * 100
        assert len(sanitize_identifier(long_name)) <= 64
