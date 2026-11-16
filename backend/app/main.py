from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from . import db, digest, runner
from .config import settings
from .sources import SOURCES
from .sources.github import CATEGORIES

logging.basicConfig(level=logging.INFO)
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    if settings.scheduler_enabled:
        scheduler.add_job(runner.run_all, "cron", hour=settings.scrape_hour, id="scrape", replace_existing=True)
        scheduler.add_job(digest.send_digest, "cron", hour=settings.digest_hour, id="digest", replace_existing=True)
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Trend Scout", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _rows(sql: str, args: list) -> list[dict]:
    with db.connect() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


@app.get("/api/health")
def health():
    return {"ok": True, "scheduler": scheduler.running}


@app.get("/api/categories")
def categories():
    return {"categories": ["trending", *CATEGORIES.keys()]}


@app.get("/api/repos")
def repos(
    category: str | None = None,
    q: str | None = None,
    language: str | None = None,
    min_stars: int = 0,
    sort: str = Query("stars", pattern="^(stars|new|period)$"),
    limit: int = Query(60, le=200),
):
    where, args = ["stars >= ?"], [min_stars]
    if category:
        where.append("category = ?")
        args.append(category)
    if language:
        where.append("LOWER(language) = LOWER(?)")
        args.append(language)
    if q:
        where.append("(full_name LIKE ? OR description LIKE ? OR topics LIKE ?)")
        args += [f"%{q}%"] * 3
    order = {"stars": "stars DESC", "new": "first_seen DESC, stars DESC", "period": "COALESCE(stars_period,0) DESC"}[sort]
    return _rows(f"SELECT * FROM repos WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ?", [*args, limit])


@app.get("/api/jobs")
def jobs(
    source: str | None = None,
    q: str | None = None,
    location: str | None = None,
    fresher_only: bool = True,
    limit: int = Query(100, le=300),
):
    where, args = ["1=1"], []
    if fresher_only:
        where.append("is_fresher = 1")
    if source:
        where.append("source = ?")
        args.append(source)
    if location:
        where.append("location LIKE ?")
        args.append(f"%{location}%")
    if q:
        where.append("(title LIKE ? OR company LIKE ? OR tags LIKE ?)")
        args += [f"%{q}%"] * 3
    return _rows(f"SELECT * FROM jobs WHERE {' AND '.join(where)} ORDER BY first_seen DESC, id DESC LIMIT ?", [*args, limit])


@app.get("/api/status")
def status():
    rows = {r["source"]: r for r in _rows("SELECT * FROM source_status", [])}
    out = []
    for name in SOURCES:
        out.append(rows.get(name) or {"source": name, "status": "never_run", "message": "", "items": 0, "last_run": None})
    return out


@app.post("/api/refresh")
async def refresh(source: str | None = None):
    only = [source] if source else None
    return await run_in_threadpool(runner.run_all, only)


@app.post("/api/digest")
async def send(dry_run: bool = True):
    return await run_in_threadpool(digest.send_digest, dry_run)
