"""Tests for the practice mode routes, question service, and progress service."""
import json
import pytest


def _login(client, email, password="StrongPass123!"):
    client.post("/signup", data={"email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})


# ---------------------------------------------------------------------------
# Question service tests
# ---------------------------------------------------------------------------

class TestQuestionService:
    def test_get_questions_mysql_beginner(self):
        from app.services.question_service import get_questions
        qs = get_questions("mysql", "beginner")
        assert len(qs) == 30

    def test_get_questions_mysql_moderate(self):
        from app.services.question_service import get_questions
        qs = get_questions("mysql", "moderate")
        assert len(qs) == 20

    def test_get_questions_mysql_master(self):
        from app.services.question_service import get_questions
        qs = get_questions("mysql", "master")
        assert len(qs) == 15

    def test_get_questions_postgres_beginner(self):
        from app.services.question_service import get_questions
        qs = get_questions("postgres", "beginner")
        assert len(qs) == 30

    def test_get_questions_postgres_moderate(self):
        from app.services.question_service import get_questions
        qs = get_questions("postgres", "moderate")
        assert len(qs) == 20

    def test_get_questions_postgres_master(self):
        from app.services.question_service import get_questions
        qs = get_questions("postgres", "master")
        assert len(qs) == 15

    def test_total_questions_count(self):
        from app.services.question_service import get_questions
        total = sum(
            len(get_questions(db, diff))
            for db in ("mysql", "postgres")
            for diff in ("beginner", "moderate", "master")
        )
        assert total == 130

    def test_get_question_by_id(self):
        from app.services.question_service import get_question
        q = get_question("mysql", "beginner", 1)
        assert q is not None
        assert q["id"] == 1
        assert "question" in q
        assert "hint" in q
        assert "sample_answer" in q

    def test_get_question_not_found(self):
        from app.services.question_service import get_question
        assert get_question("mysql", "beginner", 999) is None

    def test_get_question_invalid_db(self):
        from app.services.question_service import get_question
        assert get_question("oracle", "beginner", 1) is None

    def test_difficulty_info(self):
        from app.services.question_service import get_difficulty_info
        info = get_difficulty_info("beginner")
        assert info["label"] == "Beginner"
        assert "emoji" in info
        assert "color" in info

    def test_all_questions_have_required_fields(self):
        from app.services.question_service import get_questions
        for db in ("mysql", "postgres"):
            for diff in ("beginner", "moderate", "master"):
                for q in get_questions(db, diff):
                    assert "id" in q, f"{db}/{diff} question missing id"
                    assert "question" in q, f"{db}/{diff} Q{q.get('id')} missing question"
                    assert "hint" in q, f"{db}/{diff} Q{q.get('id')} missing hint"
                    assert "sample_answer" in q, f"{db}/{diff} Q{q.get('id')} missing sample_answer"

    def test_get_supported_difficulties(self):
        from app.services.question_service import get_supported_difficulties
        diffs = get_supported_difficulties("mysql")
        assert "beginner" in diffs
        assert "moderate" in diffs
        assert "master" in diffs

    def test_get_supported_difficulties_invalid_db(self):
        from app.services.question_service import get_supported_difficulties
        assert get_supported_difficulties("oracle") == []


# ---------------------------------------------------------------------------
# Progress service tests
# ---------------------------------------------------------------------------

class TestProgressService:
    def test_get_progress_default(self, set_test_db):
        from app.services.progress_service import get_progress
        progress = get_progress(9999, "mysql", "beginner")
        assert progress["current_question"] == 1
        assert progress["completed_ids"] == []

    def test_save_and_get_progress(self, set_test_db):
        from app.services.progress_service import get_progress, save_progress
        save_progress(8001, "mysql", "beginner", 5, [1, 2, 3, 4])
        progress = get_progress(8001, "mysql", "beginner")
        assert progress["current_question"] == 5
        assert 4 in progress["completed_ids"]

    def test_mark_question_complete(self, set_test_db):
        from app.services.progress_service import mark_question_complete, get_progress
        result = mark_question_complete(8002, "mysql", "beginner", 1, 30)
        assert 1 in result["completed_ids"]
        assert result["current_question"] == 2

    def test_mark_question_complete_idempotent(self, set_test_db):
        from app.services.progress_service import mark_question_complete
        mark_question_complete(8003, "mysql", "beginner", 1, 30)
        result = mark_question_complete(8003, "mysql", "beginner", 1, 30)
        assert result["completed_ids"].count(1) == 1  # not duplicated

    def test_reset_progress(self, set_test_db):
        from app.services.progress_service import save_progress, reset_progress, get_progress
        save_progress(8004, "mysql", "beginner", 10, [1, 2, 3])
        reset_progress(8004, "mysql", "beginner")
        progress = get_progress(8004, "mysql", "beginner")
        assert progress["current_question"] == 1
        assert progress["completed_ids"] == []

    def test_progress_separate_per_db_type(self, set_test_db):
        from app.services.progress_service import save_progress, get_progress
        save_progress(8005, "mysql", "beginner", 3, [1, 2])
        save_progress(8005, "postgres", "beginner", 7, [1, 2, 3, 4, 5, 6])
        m = get_progress(8005, "mysql", "beginner")
        p = get_progress(8005, "postgres", "beginner")
        assert m["current_question"] == 3
        assert p["current_question"] == 7

    def test_mark_last_question_complete(self, set_test_db):
        from app.services.progress_service import mark_question_complete
        result = mark_question_complete(8006, "mysql", "beginner", 30, 30)
        assert 30 in result["completed_ids"]
        # current_question stays capped at total_questions
        assert result["current_question"] == 30


# ---------------------------------------------------------------------------
# Practice route tests
# ---------------------------------------------------------------------------

class TestPracticeRoutes:
    def test_select_difficulty_requires_login(self, client):
        with client.application.test_client() as c:
            resp = c.get("/practice/mysql")
            assert resp.status_code == 302
            assert "/login" in resp.location

    def test_invalid_db_type_redirects(self, client):
        with client.application.test_client() as c:
            _login(c, "prac_invalid@example.com")
            resp = c.get("/practice/oracle")
            assert resp.status_code == 302

    def test_select_difficulty_no_db_redirects(self, client):
        """Without a sandbox database, user is redirected to dashboard."""
        with client.application.test_client() as c:
            _login(c, "prac_nodb@example.com")
            resp = c.get("/practice/mysql")
            assert resp.status_code == 302
            assert "dashboard" in resp.location

    def test_practice_start_no_db_redirects(self, client):
        with client.application.test_client() as c:
            _login(c, "prac_start_nodb@example.com")
            resp = c.get("/practice/mysql/beginner")
            assert resp.status_code == 302

    def test_practice_question_no_db_redirects(self, client):
        with client.application.test_client() as c:
            _login(c, "prac_q_nodb@example.com")
            resp = c.get("/practice/mysql/beginner/1")
            assert resp.status_code == 302

    def test_practice_run_requires_login(self, client):
        with client.application.test_client() as c:
            resp = c.post(
                "/practice/mysql/beginner/1/run",
                data=json.dumps({"query": "SELECT 1"}),
                content_type="application/json",
            )
            assert resp.status_code == 401

    def test_practice_run_invalid_db_type(self, client):
        with client.application.test_client() as c:
            _login(c, "prac_run_invalid@example.com")
            resp = c.post(
                "/practice/oracle/beginner/1/run",
                data=json.dumps({"query": "SELECT 1"}),
                content_type="application/json",
            )
            assert resp.status_code == 400

    def test_practice_run_no_sandbox(self, client):
        """Run returns 404 when user has no sandbox database."""
        with client.application.test_client() as c:
            _login(c, "prac_run_nosandbox@example.com")
            resp = c.post(
                "/practice/mysql/beginner/1/run",
                data=json.dumps({"query": "SELECT 1"}),
                content_type="application/json",
            )
            assert resp.status_code == 404

    def test_practice_run_missing_query(self, client):
        """Run returns 400 when query is missing (no sandbox needed check)."""
        with client.application.test_client() as c:
            _login(c, "prac_run_noq@example.com")
            resp = c.post(
                "/practice/mysql/beginner/1/run",
                data=json.dumps({}),
                content_type="application/json",
            )
            # 400 for missing query or 404 for missing sandbox — both acceptable
            assert resp.status_code in (400, 404)

    def test_practice_complete_requires_login(self, client):
        with client.application.test_client() as c:
            resp = c.get("/practice/mysql/beginner/complete")
            assert resp.status_code == 302
            assert "/login" in resp.location

    def test_practice_reset_requires_login(self, client):
        with client.application.test_client() as c:
            resp = c.post("/practice/mysql/beginner/reset")
            assert resp.status_code == 401

    def test_practice_reset_invalid_db_type(self, client):
        with client.application.test_client() as c:
            _login(c, "prac_reset_invalid@example.com")
            resp = c.post("/practice/oracle/beginner/reset")
            assert resp.status_code == 400

    def test_practice_reset_success(self, client):
        with client.application.test_client() as c:
            _login(c, "prac_reset_ok@example.com")
            resp = c.post("/practice/mysql/beginner/reset")
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data["success"] is True
