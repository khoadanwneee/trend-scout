"""Shared plumbing for source adapters: polite HTTP + robots.txt + result type."""
from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from ..config import settings

FRESHER_RE = (
    r"fresher|intern|thực tập|junior|entry[ -]?level|mới tốt nghiệp|"
    r"graduate|0\s*-\s*1\s*năm|không yêu cầu kinh nghiệm|trainee"
)


@dataclass
class Result:
    """Outcome of one adapter run. status: ok | empty | blocked | unsupported | disabled | error"""

    status: str
    message: str = ""
    repos: list[dict] = field(default_factory=list)
    jobs: list[dict] = field(default_factory=list)


class Blocked(Exception):
    """Site refused us (robots.txt, 403, challenge page). We stop; we never evade."""


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": settings.user_agent,
            "Accept-Language": "vi,en;q=0.8",
        },
        timeout=25,
        follow_redirects=True,
    )


def robots_allows(client: httpx.Client, url: str) -> bool:
    p = urlparse(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    try:
        r = client.get(robots_url)
    except httpx.HTTPError as e:
        raise Blocked(f"cannot read robots.txt: {e.__class__.__name__}") from e
    if r.status_code == 404:
        return True  # no robots.txt means no stated restrictions
    if r.status_code >= 400:
        raise Blocked(f"robots.txt returned HTTP {r.status_code}")
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    return rp.can_fetch(settings.user_agent, url)


def polite_get(client: httpx.Client, url: str, **kw) -> httpx.Response:
    """GET that raises Blocked on 403/429/challenge instead of retrying around it."""
    r = client.get(url, **kw)
    challenged = (
        "cf-mitigated" in r.headers
        or "Attention Required! | Cloudflare" in r.text[:2000]
        or "Just a moment..." in r.text[:2000]
    )
    if r.status_code in (401, 403, 429) or challenged:
        raise Blocked(f"HTTP {r.status_code}{' (bot challenge)' if challenged else ''}")
    r.raise_for_status()
    return r


def sleep_polite() -> None:
    time.sleep(settings.request_delay_seconds)
