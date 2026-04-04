"""End-to-end: search → scrape → extract."""

from __future__ import annotations

import asyncio
import logging

from agentic_search.extract import ExtractionResult, extract_entities
from agentic_search.scrape import fetch_page_text
from agentic_search.search import SearchHit, search_web

logger = logging.getLogger(__name__)


async def run_pipeline(topic: str) -> ExtractionResult:
    hits = await search_web(topic)

    async def one(hit: SearchHit) -> tuple[str, str]:
        if not hit.url:
            return "", ""
        if hit.extracted_text and hit.extracted_text.strip():
            return hit.url, hit.extracted_text.strip()
        text = await fetch_page_text(hit.url)
        return hit.url, text

    pairs = await asyncio.gather(*[one(h) for h in hits if h.url])
    url_text = [(u, t) for u, t in pairs if t.strip()]
    if not url_text:
        logger.warning("No page text scraped; LLM will have little context")
    return await extract_entities(topic, url_text)
