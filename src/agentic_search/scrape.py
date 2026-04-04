"""Fetch and extract readable text from HTML pages."""

from __future__ import annotations

import logging
import re

import httpx
from bs4 import BeautifulSoup

from agentic_search.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; AgenticSearchBot/1.0; +https://example.local; research)"
)


async def fetch_page_text(url: str, referer: str | None = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.scrape_timeout_s,
            headers=headers,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            if "text/html" not in ctype and "application/xhtml" not in ctype:
                return ""
    except Exception as e:
        logger.debug("fetch failed %s: %s", url, e)
        return ""

    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    if len(text) > settings.max_chars_per_page:
        text = text[: settings.max_chars_per_page] + "\n…"
    return text
