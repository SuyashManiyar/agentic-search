"""Web search via Parallel Search API only."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from agentic_search.config import settings

PARALLEL_SEARCH_URL = "https://api.parallel.ai/v1beta/search"


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str
    # Parallel returns excerpts; pipeline uses this instead of live scraping when present.
    extracted_text: str | None = None


async def search_web(query: str, limit: int | None = None) -> list[SearchHit]:
    if not (settings.parallel_api_key or "").strip():
        raise RuntimeError(
            "PARALLEL_API_KEY is not set. Add it to your .env file "
            "(see .env.example). Search uses the Parallel API only."
        )
    cap = limit if limit is not None else settings.max_search_results
    return await _search_parallel(query, cap)


async def _search_parallel(query: str, limit: int) -> list[SearchHit]:
    headers = {
        "x-api-key": settings.parallel_api_key.strip(),
        "Content-Type": "application/json",
    }
    if settings.parallel_beta_header.strip():
        headers["parallel-beta"] = settings.parallel_beta_header.strip()

    payload = {
        "objective": f"Find relevant, trustworthy sources and facts for: {query}",
        "search_queries": [query],
        "max_results": min(limit, 20),
        "excerpts": {"max_chars_per_result": settings.parallel_max_chars_per_result},
        "mode": "one-shot",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(PARALLEL_SEARCH_URL, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    hits: list[SearchHit] = []
    for item in data.get("results", [])[:limit]:
        raw_excerpts = item.get("excerpts")
        excerpts: list[str] = raw_excerpts if isinstance(raw_excerpts, list) else []
        merged = "\n\n".join(excerpts).strip() if excerpts else ""
        snippet = (
            (excerpts[0][:500] + "…")
            if excerpts and len(excerpts[0]) > 500
            else (excerpts[0] if excerpts else "")
        )
        hits.append(
            SearchHit(
                title=item.get("title") or "",
                url=item.get("url") or "",
                snippet=snippet,
                extracted_text=merged if merged else None,
            )
        )
    return hits
