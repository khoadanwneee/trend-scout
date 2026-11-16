from __future__ import annotations

import logging
import threading

from . import db
from .sources import SOURCES

log = logging.getLogger("trend-scout")
_run_lock = threading.Lock()


def run_source(name: str) -> dict:
    fn = SOURCES[name]
    try:
        res = fn()
    except Exception as e:  # one broken adapter must not stop the others
        log.exception("source %s crashed", name)
        db.set_status(name, "error", f"{e.__class__.__name__}: {e}"[:300])
        return {"source": name, "status": "error", "message": str(e)[:300], "items": 0}
    with db.connect() as c:
        for r in res.repos:
            db.upsert_repo(c, r)
        for j in res.jobs:
            db.upsert_job(c, j)
    n = len(res.repos) + len(res.jobs)
    db.set_status(name, res.status, res.message, n)
    return {"source": name, "status": res.status, "message": res.message, "items": n}


def run_all(only: list[str] | None = None) -> list[dict]:
    if not _run_lock.acquire(blocking=False):
        return [{"source": "-", "status": "busy", "message": "a run is already in progress", "items": 0}]
    try:
        names = only or list(SOURCES)
        return [run_source(n) for n in names if n in SOURCES]
    finally:
        _run_lock.release()
