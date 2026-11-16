"""ITviec: public fresher listing pages (robots.txt allows /viec-lam-it)."""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from .base import FRESHER_RE, Blocked, Result, make_client, polite_get, robots_allows, sleep_polite

LIST_URL = "https://itviec.com/viec-lam-it/fresher"


def _parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs: list[dict] = []
    for card in soup.select("div.job-card"):
        a = card.select_one("h3 a[href]")
        if not a:
            continue
        url = a["href"].split("?")[0]
        company_a = card.select_one('a[href*="nha-tuyen-dung"]:not(.logo-employer-card)')
        salary_el = card.select_one('[class*="salary"]')
        posted = card.select_one("span.small-text")
        tags = [t.get_text(strip=True) for t in card.select("a.itag, .itag")]
        # location/work-mode lines live in .text-rich-grey blocks
        rich = [e.get_text(" ", strip=True) for e in card.select(".text-rich-grey")]
        title = a.get_text(" ", strip=True)
        location = next(
            (t for t in rich if re.search(r"Hồ Chí Minh|Hà Nội|Đà Nẵng|Remote|Cần Thơ|Hải Phòng", t)),
            "",
        )
        salary = salary_el.get_text(" ", strip=True) if salary_el else ""
        if "Đăng nhập" in salary:  # "login to view salary" is not a salary
            salary = ""
        blob = f"{title} {' '.join(rich)} {' '.join(tags)}"
        jobs.append(
            {
                "source": "itviec",
                "url": url,
                "title": title,
                "company": company_a.get_text(" ", strip=True) if company_a else "",
                "location": location,
                "salary": salary,
                "tags": ",".join(tags),
                "posted_text": re.sub(r"\s+", " ", posted.get_text(" ", strip=True)) if posted else "",
                "is_fresher": 1 if re.search(FRESHER_RE, blob, re.I) else 0,
            }
        )
    return jobs


def fetch() -> Result:
    jobs: list[dict] = []
    with make_client() as client:
        try:
            if not robots_allows(client, LIST_URL):
                return Result("blocked", "robots.txt disallows listing page")
            for page in range(1, settings.itviec_pages + 1):
                r = polite_get(client, LIST_URL, params={"page": page})
                batch = _parse(r.text)
                if not batch:
                    break
                jobs.extend(batch)
                if page < settings.itviec_pages:
                    sleep_polite()
        except Blocked as e:
            if jobs:
                return Result("ok", f"partial, then stopped: {e}", jobs=jobs)
            return Result("blocked", str(e))
        except httpx.HTTPError as e:
            return Result("error", e.__class__.__name__ + f": {e}"[:200], jobs=jobs)
    if not jobs:
        return Result("empty", "page loaded but no job cards parsed (layout changed?)")
    return Result("ok", jobs=jobs)
