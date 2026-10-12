"""SQLite persistence layer.

One connection per request is stored on ``flask.g`` and closed on teardown.
"""
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username       TEXT PRIMARY KEY,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'Trainer'
);

CREATE TABLE IF NOT EXISTS clients (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT UNIQUE NOT NULL,
    age               INTEGER,
    height            REAL,
    weight            REAL,
    program           TEXT,
    calories          INTEGER,
    target_weight     REAL,
    target_adherence  INTEGER,
    membership_status TEXT NOT NULL DEFAULT 'Active',
    membership_end    TEXT
);

CREATE TABLE IF NOT EXISTS progress (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    week       TEXT NOT NULL,
    adherence  INTEGER NOT NULL CHECK (adherence BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS workouts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id     INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    date          TEXT NOT NULL,
    workout_type  TEXT NOT NULL,
    duration_min  INTEGER NOT NULL,
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS exercises (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id  INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    sets        INTEGER NOT NULL,
    reps        INTEGER NOT NULL,
    weight      REAL
);

CREATE TABLE IF NOT EXISTS metrics (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    date       TEXT NOT NULL,
    weight     REAL,
    waist      REAL,
    bodyfat    REAL
);
"""


def get_db():
    """Return the request-scoped database connection, opening it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    """Create tables if they do not exist yet (idempotent)."""
    conn = get_db()
    conn.executescript(SCHEMA)
    # Seed a default admin (as the legacy app did), but store a hash, not plain text.
    if conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone() is None:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash(
                current_app.config["ADMIN_PASSWORD"],
                method=current_app.config["PASSWORD_HASH_METHOD"],
            ), "Admin"),
        )
    conn.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
