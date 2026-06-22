"""Tests for the answer validator service."""
import pytest


class TestAnswerValidatorService:
    def test_error_result_is_incorrect(self):
        from app.services.answer_validator_service import validate_answer
        result = validate_answer({"error": "syntax error"}, None)
        assert result["is_correct"] is False
        assert "error" in result["feedback"].lower()

    def test_message_result_with_matching_expected_output(self):
        from app.services.answer_validator_service import validate_answer
        result = validate_answer(
            {"message": "Query executed successfully. Rows affected: 1"},
            "Query executed successfully",
        )
        assert result["is_correct"] is True

    def test_row_count_match(self):
        from app.services.answer_validator_service import validate_answer
        result = validate_answer(
            {"columns": ["id"], "rows": [[1], [2], [3]]},
            "3 rows returned",
        )
        assert result["is_correct"] is True

    def test_row_count_mismatch(self):
        from app.services.answer_validator_service import validate_answer
        result = validate_answer(
            {"columns": ["id"], "rows": [[1]]},
            "5 rows returned",
        )
        # Only 1 row vs expected 5 – validator should return True (open practice)
        # because we fall through to the generic "any result = correct" path
        assert result["is_correct"] is True

    def test_select_result_is_correct(self):
        from app.services.answer_validator_service import validate_answer
        result = validate_answer(
            {"columns": ["name", "salary"], "rows": [["Alice", 95000]]},
            None,
        )
        assert result["is_correct"] is True

    def test_empty_result_no_expected(self):
        from app.services.answer_validator_service import validate_answer
        # No rows, no message, no error → can't validate
        result = validate_answer({}, None)
        assert result["is_correct"] is False

    def test_ddl_message_correct(self):
        from app.services.answer_validator_service import validate_answer
        result = validate_answer(
            {"message": "Query executed successfully. Rows affected: 0"},
            "table created successfully",
        )
        # Falls through to generic path since "table created" != msg substring
        # but message exists → True
        assert result["is_correct"] is True

    def test_feedback_is_string(self):
        from app.services.answer_validator_service import validate_answer
        result = validate_answer({"message": "OK"}, None)
        assert isinstance(result["feedback"], str)
        assert len(result["feedback"]) > 0
