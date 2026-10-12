"""SQLite persistence layer.

One connection per request is stored on ``flask.g`` and closed on teardown.
"""
import sqlite3

from flask import current_app, g

SCHEMA = """
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
    conn.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
