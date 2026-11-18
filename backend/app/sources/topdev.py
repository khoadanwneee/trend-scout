"""TopDev: IT jobs for interns and new graduates, from the public search page.

TopDev is now a general job board (run with Saramin), so the search is narrowed to the roles of
its "IT" category and to the intern / new-graduate levels. The page is a Next.js app whose
results are embedded in the server-rendered payload (`self.__next_f.push` chunks); we read
that, not the site's internal API. robots.txt allows /jobs/search.
"""
from __future__ import annotations

import json
import re

import httpx

from ..config import settings
from .base import FRESHER_RE, Blocked, Result, make_client, polite_get, robots_allows, sleep_polite

SEARCH_URL = "https://topdev.vn/jobs/search"
IT_CATEGORY_ID = 1
# Roles under the IT category, as listed in the page's own filter data (checked 2026-11-17).
IT_ROLE_IDS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 67)
# Job levels: 1616 = "Thực tập", 12507 = "Mới tốt nghiệp".
FRESHER_LEVEL_IDS = (1616, 12507)

_CHUNK_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
_DECODER = json.JSONDecoder()


def search_url(page: int = 1) -> str:
    # Literal commas, the way the site's own search form writes them.
    url = (
        f"{SEARCH_URL}?job_categories_ids={','.join(map(str, IT_ROLE_IDS))}"
        f"&job_levels_ids={','.join(map(str, FRESHER_LEVEL_IDS))}"
    )
    return url if page == 1 else f"{url}&page={page}"


def _str(v) -> str:
    """RSC strings: '$$x' is a literal '$x'; any other '$...' is a reference we don't follow."""
    if not isinstance(v, str):
        return ""
    if v.startswith("$$"):
        return v[1:].strip()
    return "" if v.startswith("$") else v.strip()


def _dict(v) -> dict:
    return v if isinstance(v, dict) else {}


def _parse(html: str) -> tuple[list[dict], dict] | None:
    """(jobs, meta) from the search-results array, or None if the page has no such array.

    Only the "jobs" array directly followed by "meta" (total, last_page, ...) is the search
    result. Other "jobs" arrays on the page are unfiltered sponsored jobs and are ignored,
    except to look up company names that the results refer to instead of repeating.
    """
    text = "".join(json.loads(c) for c in _CHUNK_RE.findall(html))
    by_job: dict[int, str] = {}
    by_owner: dict[int, str] = {}
    results, meta = None, {}
    for m in re.finditer(r'"jobs":\[', text):
        try:
            arr, end = _DECODER.raw_decode(text, m.end() - 1)
        except ValueError:
            continue
        for j in arr:
            name = _str(_dict(_dict(j).get("company")).get("display_name"))
            if name:
                by_job[j.get("id")] = name
                by_owner[j.get("owned_id") or j["company"].get("id")] = name
        if text.startswith(',"meta":{', end):
            results = arr
            meta = _dict(_DECODER.raw_decode(text, end + len(',"meta":'))[0])
    if results is None:
        return None

    jobs: list[dict] = []
    for j in results:
        if not isinstance(j, dict) or j.get("job_category_id", IT_CATEGORY_ID) != IT_CATEGORY_ID:
            continue  # second guard in case the site ever ignores the category filter
        url, title = _str(j.get("detail_url")).split("?")[0], _str(j.get("title"))
        if not url or not title:
            continue
        company = _str(_dict(j.get("company")).get("display_name"))
        company = company or by_job.get(j.get("id")) or by_owner.get(j.get("owned_id"), "")
        regions = [
            re.sub(r"^(Thành phố|Tỉnh)\s+", "", _str(r))
            for r in _dict(j.get("addresses")).get("address_region_array") or []
        ]
        levels = [_str(x) for x in j.get("job_levels_arr") or []]
        skills = [_str(x) for x in j.get("skills_arr") or []]
        published = _str(_dict(j.get("published")).get("date"))
        fresher_level = set(j.get("job_levels_ids") or []) & set(FRESHER_LEVEL_IDS)
        jobs.append(
            {
                "source": "topdev",
                "url": url,
                "title": title,
                "company": company,
                "location": ", ".join(r for r in regions if r),
                "salary": _str(_dict(j.get("salary")).get("value")),
                "tags": ",".join(x for x in [*levels, *skills] if x),
                "posted_text": f"Đăng {published.replace('-', '/')}" if published else "",
                "is_fresher": 1 if fresher_level or re.search(FRESHER_RE, title, re.I) else 0,
            }
        )
    return jobs, meta


def fetch() -> Result:
    jobs: list[dict] = []
    with make_client() as client:
        try:
            if not robots_allows(client, search_url()):
                return Result("blocked", "robots.txt disallows the search page")
            for page in range(1, settings.topdev_pages + 1):
                if page > 1:
                    sleep_polite()
                parsed = _parse(polite_get(client, search_url(page)).text)
                if parsed is None:
                    if jobs:
                        break
                    return Result(
                        "empty", "no search results in the page: 0 jobs today, or the layout changed"
                    )
                batch, meta = parsed
                seen = {j["url"] for j in jobs}
                new = [j for j in batch if j["url"] not in seen]
                jobs.extend(new)
                if not new or page >= int(meta.get("last_page") or 1):
                    break
        except Blocked as e:
            if jobs:
                return Result("ok", f"partial, then stopped: {e}", jobs=jobs)
            return Result("blocked", str(e))
        except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError) as e:
            # TopDev sometimes drops the connection instead of answering: a refusal, not a bug.
            msg = f"connection dropped by the site ({e.__class__.__name__}); no retry"
            return Result("ok", f"partial, then stopped: {msg}", jobs=jobs) if jobs else Result("blocked", msg)
        except httpx.HTTPError as e:
            return Result("error", e.__class__.__name__ + f": {e}"[:200], jobs=jobs)
    if not jobs:
        return Result("empty", "no IT intern/new-graduate jobs in the search results right now")
    return Result("ok", jobs=jobs)
