-- schema_updates.sql
-- Adds the tables required for the complete SQL Learning Platform.
-- Run this against the application's SQLite database (app.db / users.db).

-- ── Questions table ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sql_questions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    database_type   TEXT    NOT NULL,           -- 'mysql' | 'postgres'
    difficulty      TEXT    NOT NULL,           -- 'beginner' | 'moderate' | 'master'
    question_number INTEGER NOT NULL,
    topic           TEXT,
    question_text   TEXT    NOT NULL,
    hint            TEXT,
    expected_sql    TEXT,
    expected_output TEXT,
    explanation     TEXT,
    sample_data     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (database_type, difficulty, question_number)
);

-- ── User answers log ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    question_id     INTEGER,                    -- references sql_questions.id if stored there
    db_type         TEXT    NOT NULL,
    difficulty      TEXT    NOT NULL,
    question_number INTEGER NOT NULL,
    submitted_sql   TEXT    NOT NULL,
    is_correct      INTEGER NOT NULL DEFAULT 0, -- 0 = false, 1 = true
    submitted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Indexes for common query patterns ─────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_user_answers_user   ON user_answers (user_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_q_num  ON user_answers (db_type, difficulty, question_number);
CREATE INDEX IF NOT EXISTS idx_sql_questions_lookup
    ON sql_questions (database_type, difficulty, question_number);
