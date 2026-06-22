"""Question service – provides question data for the practice mode."""
from app.data.questions import DIFFICULTY_LABELS, QUESTIONS


def get_questions(db_type: str, difficulty: str) -> list:
    """Return the list of questions for *db_type* and *difficulty*.

    Returns an empty list for unknown combinations.
    """
    return QUESTIONS.get(db_type, {}).get(difficulty, [])


def get_question(db_type: str, difficulty: str, question_id: int) -> dict | None:
    """Return a single question dict or *None* if not found."""
    questions = get_questions(db_type, difficulty)
    for q in questions:
        if q["id"] == question_id:
            return q
    return None


def get_difficulty_info(difficulty: str) -> dict:
    """Return label, emoji and color for a difficulty level."""
    return DIFFICULTY_LABELS.get(difficulty, {"label": difficulty, "emoji": "", "color": "#888"})


def get_supported_difficulties(db_type: str) -> list:
    """Return ordered list of difficulty keys available for *db_type*."""
    db_questions = QUESTIONS.get(db_type, {})
    order = ["beginner", "moderate", "master"]
    return [d for d in order if d in db_questions and db_questions[d]]
