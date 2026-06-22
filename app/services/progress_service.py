"""Progress service – tracks per-user practice progress in SQLite."""
import json
import logging
import sqlite3

from app.utils.db_init import DB_PATH

logger = logging.getLogger(__name__)


def _ensure_progress_table(conn: sqlite3.Connection) -> None:
    """Create the practice_progress table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_progress (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            db_type         TEXT NOT NULL,
            difficulty      TEXT NOT NULL,
            current_question INTEGER NOT NULL DEFAULT 1,
            completed_ids   TEXT NOT NULL DEFAULT '[]',
            started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, db_type, difficulty),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()


def get_progress(user_id: int, db_type: str, difficulty: str) -> dict:
    """Return progress dict for user/db_type/difficulty.

    Keys: ``current_question`` (int), ``completed_ids`` (list of int).
    Returns defaults (question 1, no completed) if no record exists.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _ensure_progress_table(conn)
        row = conn.execute(
            "SELECT current_question, completed_ids FROM practice_progress "
            "WHERE user_id = ? AND db_type = ? AND difficulty = ?",
            (user_id, db_type, difficulty),
        ).fetchone()
        conn.close()
        if row:
            try:
                completed = json.loads(row["completed_ids"])
            except (json.JSONDecodeError, TypeError):
                completed = []
            return {
                "current_question": row["current_question"],
                "completed_ids": completed,
            }
    except Exception as exc:
        logger.error("Error fetching progress for user %d: %s", user_id, exc)
    return {"current_question": 1, "completed_ids": []}


def save_progress(
    user_id: int,
    db_type: str,
    difficulty: str,
    current_question: int,
    completed_ids: list,
) -> None:
    """Upsert practice progress for user/db_type/difficulty."""
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_progress_table(conn)
        conn.execute(
            """
            INSERT INTO practice_progress
                (user_id, db_type, difficulty, current_question, completed_ids, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, db_type, difficulty)
            DO UPDATE SET
                current_question = excluded.current_question,
                completed_ids    = excluded.completed_ids,
                updated_at       = CURRENT_TIMESTAMP
            """,
            (user_id, db_type, difficulty, current_question, json.dumps(completed_ids)),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("Error saving progress for user %d: %s", user_id, exc)


def mark_question_complete(
    user_id: int,
    db_type: str,
    difficulty: str,
    question_id: int,
    total_questions: int,
) -> dict:
    """Mark *question_id* as complete and advance current_question.

    Returns updated progress dict.
    """
    progress = get_progress(user_id, db_type, difficulty)
    completed = progress["completed_ids"]
    if question_id not in completed:
        completed.append(question_id)

    next_q = question_id + 1
    if next_q > total_questions:
        next_q = total_questions  # stay at last question once finished

    save_progress(user_id, db_type, difficulty, next_q, completed)
    return {"current_question": next_q, "completed_ids": completed}


def reset_progress(user_id: int, db_type: str, difficulty: str) -> None:
    """Reset practice progress for user/db_type/difficulty."""
    save_progress(user_id, db_type, difficulty, 1, [])


def get_all_progress(user_id: int) -> list:
    """Return all practice progress rows for *user_id* (for dashboard display)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _ensure_progress_table(conn)
        rows = conn.execute(
            "SELECT db_type, difficulty, current_question, completed_ids "
            "FROM practice_progress WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            try:
                completed = json.loads(row["completed_ids"])
            except (json.JSONDecodeError, TypeError):
                completed = []
            result.append({
                "db_type": row["db_type"],
                "difficulty": row["difficulty"],
                "current_question": row["current_question"],
                "completed_count": len(completed),
            })
        return result
    except Exception as exc:
        logger.error("Error fetching all progress for user %d: %s", user_id, exc)
        return []
