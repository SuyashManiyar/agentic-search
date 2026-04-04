"""LLM extraction of structured entities with source traceability."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import APIError, AsyncOpenAI
from pydantic import BaseModel, Field

from agentic_search.config import settings

logger = logging.getLogger(__name__)

SYSTEM = """You are a research assistant. Given a user topic and excerpts from web pages (each block starts with [SOURCE_URL: ...]), extract distinct real-world entities that match the topic.

For each entity, output JSON objects with:
- "name": string
- "summary": one short sentence
- "attributes": object of extra key-value pairs the user would care about (e.g. location, category, year) — only facts supported by the provided text
- "citations": list of objects {"field": which field this supports (name|summary|attributes.<key>), "url": source URL, "quote": short verbatim quote <=200 chars from that source}

Do not invent URLs or facts not present in the excerpts. If unsure, omit the attribute or entity. Return strict JSON: {"entities": [...]}"""


class Citation(BaseModel):
    field: str
    url: str
    quote: str = Field(max_length=400)


class EntityRow(BaseModel):
    name: str
    summary: str
    attributes: dict[str, str] = Field(default_factory=dict)
    citations: list[Citation] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    entities: list[EntityRow]


def _build_user_prompt(topic: str, chunks: list[tuple[str, str]], max_chars: int) -> str:
    """Assemble user message; cap total length so Groq TPM / per-request limits are not exceeded."""
    header = f"Topic: {topic}\n\nWeb excerpts:\n"
    if len(header) >= max_chars:
        return header[:max_chars]
    parts: list[str] = [header]
    used = len(header)
    included_full = 0
    for url, text in chunks:
        block = f"[SOURCE_URL: {url}]\n{text}\n---\n"
        if used + len(block) <= max_chars:
            parts.append(block)
            used += len(block)
            included_full += 1
            continue
        room = max_chars - used
        suffix = "…[truncated]\n---\n"
        url_line = f"[SOURCE_URL: {url}]\n"
        if room <= len(url_line) + len(suffix) + 80:
            break
        take = room - len(url_line) - len(suffix)
        parts.append(f"{url_line}{text[:take]}{suffix}")
        if included_full == 0:
            logger.info(
                "LLM prompt capped (%d chars): only a truncated first excerpt fits (raise GROQ_MAX_PROMPT_CHARS for more)",
                max_chars,
            )
        else:
            logger.info(
                "LLM prompt capped (%d chars): %d full source(s), then truncated excerpt",
                max_chars,
                included_full,
            )
        return "\n".join(parts)
    if included_full < len(chunks):
        logger.info(
            "LLM prompt capped (%d chars): using %d of %d sources",
            max_chars,
            included_full,
            len(chunks),
        )
    return "\n".join(parts)


async def extract_entities(topic: str, url_text_pairs: list[tuple[str, str]]) -> ExtractionResult:
    if not settings.groq_api_key:
        logger.warning("No GROQ_API_KEY; returning empty extraction")
        return ExtractionResult(entities=[])

    client = AsyncOpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
    user = _build_user_prompt(topic, url_text_pairs, settings.groq_max_prompt_chars)

    try:
        resp = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except APIError as e:
        logger.error("Groq API error: %s", e)
        return ExtractionResult(entities=[])

    raw = resp.choices[0].message.content or "{}"
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("LLM returned non-JSON")
        return ExtractionResult(entities=[])

    entities_raw = data.get("entities")
    if not isinstance(entities_raw, list):
        return ExtractionResult(entities=[])

    entities: list[EntityRow] = []
    for item in entities_raw:
        if not isinstance(item, dict):
            continue
        try:
            entities.append(EntityRow.model_validate(item))
        except Exception as e:
            logger.debug("skip bad entity: %s", e)
    return ExtractionResult(entities=entities)
