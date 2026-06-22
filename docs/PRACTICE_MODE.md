# Practice Mode – Developer Guide

## Overview

The Practice Mode lets authenticated users work through 130 SQL exercises (65
MySQL + 65 PostgreSQL) split across three difficulty tiers: **Beginner**,
**Moderate**, and **Master**.

Each question is answered in a Monaco-powered SQL editor. When the user clicks
**Run Query** the query is executed against their personal sandbox database.
A query-type-specific visual animation plays in the *Database Visualisation*
panel to illustrate how the SQL statement interacts with the tables.

---

## Directory Layout

```
app/
├── data/
│   └── questions.py               ← All 130 questions (Python source of truth)
├── routes/
│   ├── practice.py                ← Practice page routes + run endpoint
│   ├── api_questions.py           ← JSON API for questions & animation data
│   └── api_progress.py            ← JSON API for reading/writing user progress
├── services/
│   ├── question_service.py        ← Load questions by db_type / difficulty
│   ├── progress_service.py        ← Save & load per-user progress (SQLite)
│   ├── answer_validator_service.py← Validate a query result vs expected output
│   ├── query_parser_service.py    ← Detect SQL operation type (SELECT/INSERT…)
│   └── visualizer_service.py      ← Produce animation metadata per query type
├── static/
│   ├── css/
│   │   ├── practice_mode.css          ← Practice page layout
│   │   ├── animations.css             ← CSS keyframe animations
│   │   └── database_visualization.css ← DB schema panel styles
│   └── js/
│       ├── query_parser.js        ← Client-side SQL type detection
│       ├── animations.js          ← Per-operation animation functions
│       ├── visualizer_engine.js   ← Animation orchestrator + schema renderer
│       ├── progress_tracker.js    ← Fetch wrappers for progress API
│       └── practice_mode.js       ← Main page controller
└── templates/
    ├── practice_select.html       ← Difficulty selector
    ├── practice_question.html     ← Question + editor + visualization
    └── practice_complete.html     ← Completion / certificate screen

database/
├── schema_updates.sql             ← Additional tables (sql_questions, user_answers)
├── questions_mysql.sql            ← INSERT statements for MySQL questions
└── questions_postgresql.sql       ← INSERT statements for PostgreSQL questions

tests/
├── test_practice.py               ← Route, question service, progress service tests
├── test_questions.py              ← API route + query parser + visualizer tests
└── test_answer_validation.py      ← Answer validator unit tests
```

---

## Question Data

All questions live in `app/data/questions.py` as plain Python lists.  The
`question_service` reads from this module at runtime – no database queries are
needed to serve questions.

### Question Schema

```python
{
    "id":            int,          # 1-based within db_type+difficulty
    "topic":         str,          # e.g. "SELECT Basics"
    "question":      str,          # Question text shown to the user
    "hint":          str,          # Revealed on "Show Hint" click
    "sample_answer": str,          # Model answer shown after first attempt
}
```

### Counts

| Database   | Beginner | Moderate | Master | Total |
|------------|----------|----------|--------|-------|
| MySQL      | 30       | 20       | 15     | 65    |
| PostgreSQL | 30       | 20       | 15     | 65    |
| **Total**  | **60**   | **40**   | **30** | **130** |

---

## API Endpoints

### Questions

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/questions/<db_type>/<difficulty>` | List all questions |
| `GET`  | `/api/questions/<db_type>/<difficulty>/<qid>` | Single question |
| `GET`  | `/api/visualizer/animation-data?query_type=SELECT` | Animation metadata |

### Progress (requires login)

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/progress/<db_type>/<difficulty>` | Get progress |
| `POST` | `/api/progress/<db_type>/<difficulty>` | Save progress |
| `GET`  | `/api/progress` | All progress rows |

### Practice (requires login + sandbox DB)

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/practice/<db_type>` | Difficulty selector |
| `GET`  | `/practice/<db_type>/<difficulty>` | Resume / start |
| `GET`  | `/practice/<db_type>/<difficulty>/<qid>` | Specific question |
| `POST` | `/practice/<db_type>/<difficulty>/<qid>/run` | Run query |
| `GET`  | `/practice/<db_type>/<difficulty>/complete` | Completion screen |
| `POST` | `/practice/<db_type>/<difficulty>/reset` | Reset progress |

The `/run` endpoint now returns `query_type` and `animation_data` in its
JSON response so the frontend visualiser can trigger the correct animation.

---

## Visual Animation System

### Flow

```
User clicks Run Query
       │
       ▼
query_parser.js detects operation type (SELECT / INSERT / …)
       │
       ▼
animations.js plays optimistic animation immediately
       │
       ▼
fetch() sends query to /practice/.../run
       │
       ▼
Server returns result + animation_data
       │
       ▼
visualizer_engine.js triggers server-confirmed animation
```

### Animation Types

| Query Type | Duration | Colour  | Effect |
|------------|----------|---------|--------|
| SELECT     | 3 s      | Blue    | Table glows, rows fly to result panel |
| INSERT     | 3.5 s    | Green   | New row bounces in |
| UPDATE     | 3.5 s    | Orange  | Affected cells flash |
| DELETE     | 3.5 s    | Red     | Row fades and slides away |
| CREATE     | 3.5 s    | Purple  | Table scales in, columns stagger |
| ALTER      | 3 s      | Purple  | Table pulses |
| DROP       | 3 s      | Red     | Table pulses |
| OTHER      | 2 s      | Grey    | Subtle glow |

CSS animations are defined in `animations.css` using `@keyframes`.
JavaScript orchestration lives in `animations.js` and is invoked through
`visualizer_engine.js`.

---

## Progress Tracking

Progress is stored in the `practice_progress` SQLite table (created on first
access by `progress_service.py`).

```sql
CREATE TABLE practice_progress (
    id               INTEGER PRIMARY KEY,
    user_id          INTEGER NOT NULL,
    db_type          TEXT    NOT NULL,
    difficulty       TEXT    NOT NULL,
    current_question INTEGER NOT NULL DEFAULT 1,
    completed_ids    TEXT    NOT NULL DEFAULT '[]',  -- JSON array
    started_at       TIMESTAMP,
    updated_at       TIMESTAMP,
    UNIQUE(user_id, db_type, difficulty)
);
```

`completed_ids` is stored as a JSON array string (e.g. `[1, 3, 5]`).

---

## Running Tests

```bash
# All tests
pytest

# Practice-mode tests only
pytest tests/test_practice.py tests/test_questions.py tests/test_answer_validation.py -v
```

---

## Deployment Notes

* No extra environment variables are needed for the practice mode.
* The `practice_progress` and `user_answers` tables are created automatically
  on first use via `CREATE TABLE IF NOT EXISTS`.
* The SQL files in `database/` are for reference and manual seeding only; the
  app serves questions from `app/data/questions.py` at runtime.
