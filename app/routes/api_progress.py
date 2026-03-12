"""API routes for user progress – JSON responses.

Routes:
  GET  /api/progress/<db_type>/<difficulty>   → get progress for current user
  POST /api/progress/<db_type>/<difficulty>   → save / update progress
"""
from flask import Blueprint, jsonify, request, session

from app.services.progress_service import (
    get_all_progress,
    get_progress,
    save_progress,
)

api_progress_bp = Blueprint("api_progress", __name__)

_VALID_DB_TYPES    = {"mysql", "postgres"}
_VALID_DIFFICULTIES = {"beginner", "moderate", "master"}


def _require_auth():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None


@api_progress_bp.route("/api/progress/<db_type>/<difficulty>")
def get_user_progress(db_type, difficulty):
    """Return progress for the authenticated user."""
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return jsonify({"error": "Invalid db_type or difficulty"}), 400

    user_id  = session["user_id"]
    progress = get_progress(user_id, db_type, difficulty)
    return jsonify({
        "db_type":          db_type,
        "difficulty":       difficulty,
        "current_question": progress["current_question"],
        "completed_ids":    progress["completed_ids"],
        "completed_count":  len(progress["completed_ids"]),
    })


@api_progress_bp.route("/api/progress/<db_type>/<difficulty>", methods=["POST"])
def save_user_progress(db_type, difficulty):
    """Save / update progress for the authenticated user."""
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    if db_type not in _VALID_DB_TYPES or difficulty not in _VALID_DIFFICULTIES:
        return jsonify({"error": "Invalid db_type or difficulty"}), 400

    data = request.get_json(silent=True) or {}
    current_question = data.get("current_question", 1)
    completed_ids    = data.get("completed_ids", [])

    if not isinstance(current_question, int) or current_question < 1:
        return jsonify({"error": "current_question must be a positive integer"}), 400
    if not isinstance(completed_ids, list):
        return jsonify({"error": "completed_ids must be an array"}), 400

    user_id = session["user_id"]
    save_progress(user_id, db_type, difficulty, current_question, completed_ids)
    return jsonify({"success": True})


@api_progress_bp.route("/api/progress")
def get_all_user_progress():
    """Return all progress rows for the authenticated user."""
    auth_error = _require_auth()
    if auth_error:
        return auth_error

    user_id  = session["user_id"]
    progress = get_all_progress(user_id)
    return jsonify({"progress": progress})
