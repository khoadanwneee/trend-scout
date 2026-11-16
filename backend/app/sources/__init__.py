from __future__ import annotations

from collections.abc import Callable

from . import github, itviec, restricted
from .base import Result

# name -> callable returning Result
SOURCES: dict[str, Callable[[], Result]] = {
    "github-categories": github.fetch_categories,
    "github-trending": github.fetch_trending,
    "itviec": itviec.fetch,
    "topcv": restricted.fetch_topcv,
    "topdev": restricted.fetch_topdev,
    "vietnamworks": restricted.fetch_vietnamworks,
    "linkedin": restricted.fetch_linkedin,
}
