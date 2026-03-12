"""API routes for questions – JSON responses.

Routes:
  GET  /api/questions/<db_type>/<difficulty>        → list of questions
  GET  /api/questions/<db_type>/<difficulty>/<qid>  → single question
  GET  /api/visualizer/animation-data               → animation data for a query type
"""
from flask import Blueprint, jsonify, request

from app.services.query_parser_service import parse_query_type
from app.services.question_service import get_difficulty_info, get_question, get_questions
from app.services.visualizer_service import get_animation_data

api_questions_bp = Blueprint("api_questions", __name__)

_VALID_DB_TYPES    = {"mysql", "postgres"}
_VALID_DIFFICULTIES = {"beginner", "moderate", "master"}


@api_questions_bp.route("/api/questions/<db_type>/<difficulty>")
def list_questions(db_type, difficulty):
    """Return the full list of questions for *db_type* / *difficulty*."""
    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return jsonify({"error": "Invalid db_type or difficulty"}), 400

    questions = get_questions(db_type, difficulty)
    diff_info = get_difficulty_info(difficulty)
    return jsonify({
        "db_type":    db_type,
        "difficulty": difficulty,
        "diff_info":  diff_info,
        "total":      len(questions),
        "questions":  questions,
    })


@api_questions_bp.route("/api/questions/<db_type>/<difficulty>/<int:qid>")
def get_single_question(db_type, difficulty, qid):
    """Return a single question by its 1-based ID."""
    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return jsonify({"error": "Invalid db_type or difficulty"}), 400

    question = get_question(db_type, difficulty, qid)
    if question is None:
        return jsonify({"error": "Question not found"}), 404

    questions = get_questions(db_type, difficulty)
    diff_info = get_difficulty_info(difficulty)
    return jsonify({
        "db_type":         db_type,
        "difficulty":      difficulty,
        "diff_info":       diff_info,
        "question":        question,
        "question_number": qid,
        "total":           len(questions),
    })


@api_questions_bp.route("/api/visualizer/animation-data")
def animation_data():
    """Return animation metadata for a SQL query type.

    Query params:
      ``query_type`` – one of SELECT, INSERT, UPDATE, DELETE, CREATE (default: OTHER)
      ``sql``        – raw SQL string; query_type is inferred if not provided
    """
    sql        = request.args.get("sql", "")
    query_type = request.args.get("query_type", "").upper()

    if not query_type and sql:
        query_type = parse_query_type(sql)

    if not query_type:
        query_type = "OTHER"

    return jsonify(get_animation_data(query_type))
