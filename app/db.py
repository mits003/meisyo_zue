"""SQLite storage: connection helper and schema initialization."""

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pois (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    osm_type         TEXT NOT NULL,
    osm_id           INTEGER NOT NULL,
    name             TEXT NOT NULL,
    lat              REAL NOT NULL,
    lng              REAL NOT NULL,
    category         TEXT NOT NULL,
    suggested_subcat TEXT,
    tags_json        TEXT,
    UNIQUE(osm_type, osm_id)
);

CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    poi_id      INTEGER REFERENCES pois(id) ON DELETE SET NULL,
    spot_name   TEXT NOT NULL,
    lat         REAL NOT NULL,
    lng         REAL NOT NULL,
    category    TEXT NOT NULL,
    subcategory TEXT,
    author      TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '',
    comment     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
CREATE INDEX IF NOT EXISTS idx_pois_name ON pois(name);
"""


def get_connection() -> sqlite3.Connection:
    """Open a connection with Row access and foreign keys enabled."""
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they do not exist. Safe to call repeatedly."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
