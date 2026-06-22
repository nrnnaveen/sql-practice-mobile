"""Tests for the question API routes and query parser / visualizer services."""
import json
import pytest


# ---------------------------------------------------------------------------
# Query parser service
# ---------------------------------------------------------------------------

class TestQueryParserService:
    def test_select(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("SELECT * FROM employees") == "SELECT"

    def test_insert(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("INSERT INTO employees VALUES (1, 'Alice')") == "INSERT"

    def test_update(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("UPDATE employees SET salary = 50000") == "UPDATE"

    def test_delete(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("DELETE FROM employees WHERE id = 1") == "DELETE"

    def test_create(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("CREATE TABLE test (id INT)") == "CREATE"

    def test_alter(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("ALTER TABLE employees ADD COLUMN email VARCHAR(100)") == "ALTER"

    def test_drop(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("DROP TABLE old_table") == "DROP"

    def test_cte_with_select(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("WITH cte AS (SELECT 1) SELECT * FROM cte") == "SELECT"

    def test_empty_string(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("") == "OTHER"

    def test_none_string(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type(None) == "OTHER"

    def test_comment_stripped(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("-- just a comment\nSELECT 1") == "SELECT"

    def test_multiline_comment_stripped(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("/* comment */ INSERT INTO t VALUES (1)") == "INSERT"

    def test_show(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("SHOW TABLES") == "OTHER"

    def test_case_insensitive(self):
        from app.services.query_parser_service import parse_query_type
        assert parse_query_type("select * from employees") == "SELECT"


# ---------------------------------------------------------------------------
# Visualizer service
# ---------------------------------------------------------------------------

class TestVisualizerService:
    def test_select_animation(self):
        from app.services.visualizer_service import get_animation_data
        data = get_animation_data("SELECT")
        assert data["query_type"] == "SELECT"
        assert "steps" in data
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0

    def test_insert_animation(self):
        from app.services.visualizer_service import get_animation_data
        data = get_animation_data("INSERT")
        assert data["query_type"] == "INSERT"
        assert data["color"] is not None

    def test_update_animation(self):
        from app.services.visualizer_service import get_animation_data
        data = get_animation_data("UPDATE")
        assert data["query_type"] == "UPDATE"

    def test_delete_animation(self):
        from app.services.visualizer_service import get_animation_data
        data = get_animation_data("DELETE")
        assert data["query_type"] == "DELETE"

    def test_create_animation(self):
        from app.services.visualizer_service import get_animation_data
        data = get_animation_data("CREATE")
        assert data["query_type"] == "CREATE"

    def test_unknown_type_returns_default(self):
        from app.services.visualizer_service import get_animation_data
        data = get_animation_data("UNKNOWN_OP")
        assert "steps" in data
        assert data["duration_ms"] > 0

    def test_all_animation_data_have_required_keys(self):
        from app.services.visualizer_service import get_animation_data
        for qt in ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "OTHER"):
            data = get_animation_data(qt)
            assert "query_type" in data
            assert "color" in data
            assert "duration_ms" in data
            assert "description" in data
            assert "steps" in data


# ---------------------------------------------------------------------------
# API question routes
# ---------------------------------------------------------------------------

class TestAPIQuestionRoutes:
    def test_list_questions_mysql_beginner(self, client):
        resp = client.get("/api/questions/mysql/beginner")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total"] == 30
        assert len(data["questions"]) == 30

    def test_list_questions_postgres_moderate(self, client):
        resp = client.get("/api/questions/postgres/moderate")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total"] == 20

    def test_list_questions_invalid_db(self, client):
        resp = client.get("/api/questions/oracle/beginner")
        assert resp.status_code == 400

    def test_list_questions_invalid_difficulty(self, client):
        resp = client.get("/api/questions/mysql/impossible")
        assert resp.status_code == 400

    def test_get_single_question(self, client):
        resp = client.get("/api/questions/mysql/beginner/1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["question"]["id"] == 1
        assert "hint" in data["question"]

    def test_get_single_question_not_found(self, client):
        resp = client.get("/api/questions/mysql/beginner/999")
        assert resp.status_code == 404

    def test_animation_data_select(self, client):
        resp = client.get("/api/visualizer/animation-data?query_type=SELECT")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["query_type"] == "SELECT"
        assert len(data["steps"]) > 0

    def test_animation_data_from_sql(self, client):
        resp = client.get("/api/visualizer/animation-data?sql=INSERT+INTO+t+VALUES+(1)")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["query_type"] == "INSERT"

    def test_animation_data_defaults_to_other(self, client):
        resp = client.get("/api/visualizer/animation-data")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "query_type" in data


# ---------------------------------------------------------------------------
# API progress routes
# ---------------------------------------------------------------------------

class TestAPIProgressRoutes:
    def _login(self, c, email):
        c.post("/signup", data={"email": email, "password": "StrongPass123!"})
        c.post("/login",  data={"email": email, "password": "StrongPass123!"})

    def test_progress_requires_auth(self, client):
        with client.application.test_client() as c:
            resp = c.get("/api/progress/mysql/beginner")
            assert resp.status_code == 401

    def test_progress_invalid_db(self, client):
        with client.application.test_client() as c:
            self._login(c, "prog_api_bad_db@example.com")
            resp = c.get("/api/progress/oracle/beginner")
            assert resp.status_code == 400

    def test_progress_get_and_save(self, client):
        with client.application.test_client() as c:
            self._login(c, "prog_api_ok@example.com")
            # GET default
            resp = c.get("/api/progress/mysql/beginner")
            assert resp.status_code == 200
            d = json.loads(resp.data)
            assert d["current_question"] == 1
            assert d["completed_ids"] == []

            # POST update
            resp = c.post(
                "/api/progress/mysql/beginner",
                data=json.dumps({"current_question": 5, "completed_ids": [1, 2, 3, 4]}),
                content_type="application/json",
            )
            assert resp.status_code == 200

            # GET updated
            resp = c.get("/api/progress/mysql/beginner")
            d = json.loads(resp.data)
            assert d["current_question"] == 5
            assert 4 in d["completed_ids"]

    def test_progress_post_invalid_body(self, client):
        with client.application.test_client() as c:
            self._login(c, "prog_api_bad_body@example.com")
            resp = c.post(
                "/api/progress/mysql/beginner",
                data=json.dumps({"current_question": -1, "completed_ids": []}),
                content_type="application/json",
            )
            assert resp.status_code == 400

    def test_get_all_progress(self, client):
        with client.application.test_client() as c:
            self._login(c, "prog_api_all@example.com")
            resp = c.get("/api/progress")
            assert resp.status_code == 200
            d = json.loads(resp.data)
            assert "progress" in d
