-- SQL Practice Mobile – SQLite schema (users.db)
-- This file documents the local SQLite schema.
-- The database is created automatically by app/utils/db_init.py.

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL DEFAULT '',
    name        TEXT,
    picture     TEXT,
    google_id   TEXT,

    -- Per-user sandbox database tracking (ONE database per user)
    db_created  INTEGER NOT NULL DEFAULT 0,   -- 0 = not created, 1 = created
    db_type     TEXT,                          -- 'mysql' or 'postgres'
    db_name     TEXT,                          -- e.g. sandbox_johndoe
    db_user     TEXT,                          -- custom username chosen by user
    db_password TEXT,                          -- Fernet-encrypted password
    db_host     TEXT,
    db_port     INTEGER
);

CREATE TABLE IF NOT EXISTS query_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    query          TEXT NOT NULL,
    database_type  TEXT,
    execution_time REAL,
    success        INTEGER NOT NULL DEFAULT 1,
    error_message  TEXT,
    executed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_query_history_user
    ON query_history (user_id, executed_at DESC);

CREATE TABLE IF NOT EXISTS bookmarks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    name          TEXT NOT NULL,
    query         TEXT NOT NULL,
    description   TEXT,
    database_type TEXT NOT NULL DEFAULT 'mysql',
    tags          TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id          INTEGER PRIMARY KEY,
    theme            TEXT NOT NULL DEFAULT 'dark',
    default_database TEXT NOT NULL DEFAULT 'mysql',
    results_per_page INTEGER NOT NULL DEFAULT 100,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
