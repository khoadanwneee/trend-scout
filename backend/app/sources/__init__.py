from __future__ import annotations

from collections.abc import Callable

from . import github, itviec, restricted, topdev
from .base import Result

# name -> callable returning Result
SOURCES: dict[str, Callable[[], Result]] = {
    "github-categories": github.fetch_categories,
    "github-trending": github.fetch_trending,
    "itviec": itviec.fetch,
    "topcv": restricted.fetch_topcv,
    "topdev": topdev.fetch,
    "vietnamworks": restricted.fetch_vietnamworks,
    "linkedin": restricted.fetch_linkedin,
}
