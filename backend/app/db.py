from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import settings

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    category TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    language TEXT,
    stars INTEGER DEFAULT 0,
    forks INTEGER DEFAULT 0,
    stars_period INTEGER,
    topics TEXT,
    source TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE(full_name, category)
);
CREATE INDEX IF NOT EXISTS idx_repos_cat ON repos(category, stars DESC);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    salary TEXT,
    tags TEXT,
    posted_text TEXT,
    is_fresher INTEGER DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE(source, url)
);
CREATE INDEX IF NOT EXISTS idx_jobs_seen ON jobs(first_seen DESC);

CREATE TABLE IF NOT EXISTS source_status (
    source TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    message TEXT,
    items INTEGER DEFAULT 0,
    last_run TEXT
);

CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db() -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        c.executescript(SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = sqlite3.connect(settings.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def upsert_repo(c: sqlite3.Connection, r: dict) -> None:
    t = now()
    c.execute(
        """INSERT INTO repos(full_name, category, url, description, language, stars, forks,
                             stars_period, topics, source, first_seen, last_seen)
           VALUES(:full_name,:category,:url,:description,:language,:stars,:forks,
                  :stars_period,:topics,:source,:t,:t)
           ON CONFLICT(full_name, category) DO UPDATE SET
             description=excluded.description, language=excluded.language,
             stars=excluded.stars, forks=excluded.forks,
             stars_period=excluded.stars_period, topics=excluded.topics,
             last_seen=excluded.last_seen""",
        {**r, "t": t},
    )


def upsert_job(c: sqlite3.Connection, j: dict) -> None:
    t = now()
    c.execute(
        """INSERT INTO jobs(source, url, title, company, location, salary, tags,
                            posted_text, is_fresher, first_seen, last_seen)
           VALUES(:source,:url,:title,:company,:location,:salary,:tags,
                  :posted_text,:is_fresher,:t,:t)
           ON CONFLICT(source, url) DO UPDATE SET
             title=excluded.title, company=excluded.company, location=excluded.location,
             salary=excluded.salary, tags=excluded.tags, posted_text=excluded.posted_text,
             is_fresher=excluded.is_fresher, last_seen=excluded.last_seen""",
        {**j, "t": t},
    )


def set_status(source: str, status: str, message: str = "", items: int = 0) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO source_status(source,status,message,items,last_run)
               VALUES(?,?,?,?,?)
               ON CONFLICT(source) DO UPDATE SET status=excluded.status,
                 message=excluded.message, items=excluded.items, last_run=excluded.last_run""",
            (source, status, message, items, now()),
        )


def kv_get(key: str, default: str | None = None) -> str | None:
    with connect() as c:
        row = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def kv_set(key: str, value: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO kv(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
