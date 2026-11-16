"""Daily digest: items first seen since the previous digest, sent to Telegram (or printed)."""
from __future__ import annotations

import html

import httpx

from . import db
from .config import settings

TG_LIMIT = 4000  # Telegram caps messages at 4096 chars


def _esc(s: str | None) -> str:
    return html.escape(s or "", quote=False)


def build_messages(since: str | None) -> tuple[list[str], dict]:
    since = since or "1970-01-01T00:00:00Z"
    with db.connect() as c:
        repos = c.execute(
            """SELECT * FROM repos WHERE first_seen > ? AND category != 'trending'
               ORDER BY stars DESC LIMIT 60""",
            (since,),
        ).fetchall()
        trending = c.execute(
            """SELECT * FROM repos WHERE category='trending' AND first_seen > ?
               ORDER BY COALESCE(stars_period,0) DESC LIMIT 8""",
            (since,),
        ).fetchall()
        jobs = c.execute(
            """SELECT * FROM jobs WHERE first_seen > ? AND is_fresher=1
               ORDER BY first_seen DESC LIMIT 30""",
            (since,),
        ).fetchall()

    lines: list[str] = ["<b>Trend Scout digest</b>"]
    if trending:
        lines.append("\n<b>GitHub Trending (tuần)</b>")
        for r in trending:
            lines.append(
                f'• <a href="{r["url"]}">{_esc(r["full_name"])}</a> '
                f'+{r["stars_period"] or 0}★ {_esc(r["language"])} – {_esc((r["description"] or "")[:90])}'
            )
    by_cat: dict[str, list] = {}
    for r in repos:
        by_cat.setdefault(r["category"], []).append(r)
    for cat, rs in by_cat.items():
        lines.append(f"\n<b>Repo mới – {_esc(cat)}</b>")
        for r in rs[:4]:
            lines.append(
                f'• <a href="{r["url"]}">{_esc(r["full_name"])}</a> '
                f'{r["stars"]}★ – {_esc((r["description"] or "")[:90])}'
            )
    if jobs:
        lines.append("\n<b>Job fresher mới</b>")
        for j in jobs:
            extra = " · ".join(x for x in (j["company"], j["location"], j["salary"]) if x)
            lines.append(f'• <a href="{j["url"]}">{_esc(j["title"])}</a> – {_esc(extra)}')
    if len(lines) == 1:
        lines.append("\nKhông có mục mới từ lần gửi trước.")

    msgs: list[str] = []
    cur = ""
    for ln in lines:
        if len(cur) + len(ln) + 1 > TG_LIMIT:
            msgs.append(cur)
            cur = ""
        cur += ln + "\n"
    if cur:
        msgs.append(cur)
    stats = {"repos": len(repos), "trending": len(trending), "jobs": len(jobs)}
    return msgs, stats


def send_digest(dry_run: bool = False) -> dict:
    since = db.kv_get("last_digest_at")
    msgs, stats = build_messages(since)
    if not any(stats.values()):
        # Don't ping the user with an empty message on days with nothing new.
        return {"sent": False, "reason": "nothing new since last digest", "stats": stats, "messages": msgs}
    have_creds = bool(settings.telegram_bot_token and settings.telegram_chat_id)
    if dry_run or not have_creds:
        reason = "dry-run" if dry_run else "Telegram credentials missing (set TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)"
        return {"sent": False, "reason": reason, "stats": stats, "messages": msgs}
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    with httpx.Client(timeout=20) as client:
        for m in msgs:
            r = client.post(
                url,
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": m,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            if r.status_code != 200:
                return {"sent": False, "reason": f"Telegram HTTP {r.status_code}", "stats": stats, "messages": msgs}
    db.kv_set("last_digest_at", db.now())
    return {"sent": True, "reason": "ok", "stats": stats, "messages": msgs}
