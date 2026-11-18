"""Adapters for sites that currently refuse automated access (or expose no public listing data).

Each makes at most one ordinary request, reports the true outcome, and stops. None of them
tries to evade Cloudflare, captchas, TLS fingerprinting or robots.txt.
"""
from __future__ import annotations

import httpx

from ..config import settings
from .base import Blocked, Result, make_client, polite_get, robots_allows

TOPCV_URL = "https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026?exp=1"
LINKEDIN_URL = "https://www.linkedin.com/jobs/search/?keywords=fresher"


def _probe(url: str, name: str) -> Result:
    with make_client() as client:
        try:
            if not robots_allows(client, url):
                return Result("blocked", f"{name}: robots.txt disallows this page")
            polite_get(client, url)
        except Blocked as e:
            return Result("blocked", f"{name}: {e}. Stopped; no bypass attempted.")
        except httpx.HTTPError as e:
            return Result(
                "blocked",
                f"{name}: connection refused/closed ({e.__class__.__name__}). "
                "Treated as blocked; no bypass attempted.",
            )
    return Result(
        "unsupported",
        f"{name}: page is reachable but no parser has been written for it yet.",
    )


def fetch_topcv() -> Result:
    return _probe(TOPCV_URL, "TopCV")


def fetch_vietnamworks() -> Result:
    # The public HTML only embeds ~5 sponsored jobs; the real search results come from an
    # undocumented internal API. We don't call undocumented endpoints, so nothing to fetch.
    return Result(
        "unsupported",
        "VietnamWorks: public pages embed only a few sponsored jobs; full search results "
        "are served by an internal API that is not intended for third parties.",
    )


def fetch_linkedin() -> Result:
    if not settings.enable_linkedin:
        return Result(
            "disabled",
            "LinkedIn: disabled. Its robots.txt and User Agreement prohibit automated "
            "scraping; use LinkedIn's own job alerts instead.",
        )
    with make_client() as client:
        try:
            if not robots_allows(client, LINKEDIN_URL):
                return Result("blocked", "LinkedIn: robots.txt disallows this path.")
        except Blocked as e:
            return Result("blocked", f"LinkedIn: {e}")
        except httpx.HTTPError as e:
            return Result("blocked", f"LinkedIn: connection failed ({e.__class__.__name__})")
    return Result("unsupported", "LinkedIn: scraping is prohibited by its User Agreement.")
