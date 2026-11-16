"""GitHub: Search API per category (topics) + scraped weekly Trending page.

Trending HTML has no category data, so categories come from topic searches.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from .base import Blocked, Result, make_client, polite_get, robots_allows

# category -> GitHub topics to query (one request per topic)
CATEGORIES: dict[str, list[str]] = {
    "frontend": ["frontend", "react"],
    "backend": ["backend", "microservices"],
    "design-ui": ["ui-design", "design-system"],
    "ux": ["ux", "user-experience"],
    "data": ["data-science", "data-engineering"],
    "video": ["video-editing", "ffmpeg"],
    "writing": ["writing", "technical-writing"],
    "ai": ["llm", "ai-agents"],
}

API = "https://api.github.com/search/repositories"


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": settings.user_agent,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


def _to_repo(item: dict, category: str, source: str) -> dict:
    return {
        "full_name": item["full_name"],
        "category": category,
        "url": item["html_url"],
        "description": item.get("description"),
        "language": item.get("language"),
        "stars": item.get("stargazers_count", 0),
        "forks": item.get("forks_count", 0),
        "stars_period": None,
        "topics": ",".join(item.get("topics", [])),
        "source": source,
    }


def _search(client: httpx.Client, q: str, per_page: int = 15) -> list[dict]:
    r = client.get(
        API,
        params={"q": q, "sort": "stars", "order": "desc", "per_page": per_page},
        headers=_headers(),
    )
    if r.status_code in (403, 429):
        raise Blocked(f"GitHub API rate limited (HTTP {r.status_code}); set GITHUB_TOKEN")
    r.raise_for_status()
    return r.json().get("items", [])


def fetch_categories() -> Result:
    # unauthenticated search limit is 10 req/min; authenticated 30 req/min
    gap = 2.2 if settings.github_token else 6.5
    since_new = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
    since_push = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
    repos: list[dict] = []
    notes: list[str] = []
    with make_client() as client:
        for category, topics in CATEGORIES.items():
            for topic in topics:
                # "hot": recently created and already starred; fall back to recently active
                try:
                    items = _search(client, f"topic:{topic} created:>{since_new} stars:>20")
                    time.sleep(gap)
                    if len(items) < 5:
                        items += _search(client, f"topic:{topic} pushed:>{since_push} stars:>500")
                        time.sleep(gap)
                except Blocked as e:
                    notes.append(str(e))
                    if repos:
                        return Result("ok", "partial: " + notes[-1], repos=repos)
                    return Result("blocked", notes[-1])
                except httpx.HTTPError as e:
                    notes.append(f"{topic}: {e.__class__.__name__}")
                    continue
                for it in items:
                    repos.append(_to_repo(it, category, "github-search"))
    status = "ok" if repos else "empty"
    return Result(status, "; ".join(notes[:3]), repos=repos)


def fetch_trending(since: str = "weekly") -> Result:
    url = f"https://github.com/trending?since={since}"
    with make_client() as client:
        try:
            if not robots_allows(client, url):
                return Result("blocked", "robots.txt disallows /trending")
            r = polite_get(client, url)
        except Blocked as e:
            return Result("blocked", str(e))
        except httpx.HTTPError as e:
            return Result("error", e.__class__.__name__)
    soup = BeautifulSoup(r.text, "lxml")
    repos: list[dict] = []
    for art in soup.select("article.Box-row"):
        a = art.select_one("h2 a")
        if not a:
            continue
        full = "".join(a.get_text().split())  # "owner/name"
        desc = art.select_one("p")
        lang = art.select_one('[itemprop="programmingLanguage"]')
        stars_total = 0
        forks = 0
        for link in art.select("a.Link--muted"):
            href = link.get("href", "")
            num = "".join(ch for ch in link.get_text() if ch.isdigit())
            if href.endswith("/stargazers") and num:
                stars_total = int(num)
            elif href.endswith("/forks") and num:
                forks = int(num)
        period = 0
        for sp in art.select("span.d-inline-block.float-sm-right"):
            digits = "".join(ch for ch in sp.get_text() if ch.isdigit())
            if digits:
                period = int(digits)
        repos.append(
            {
                "full_name": full,
                "category": "trending",
                "url": f"https://github.com/{full}",
                "description": desc.get_text(strip=True) if desc else None,
                "language": lang.get_text(strip=True) if lang else None,
                "stars": stars_total,
                "forks": forks,
                "stars_period": period,
                "topics": "",
                "source": f"github-trending-{since}",
            }
        )
    if not repos:
        return Result("empty", "Trending page parsed but no repos found (layout changed?)")
    return Result("ok", repos=repos)
