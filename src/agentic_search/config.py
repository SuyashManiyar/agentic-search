from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of `src/` (works no matter what cwd is).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Groq (OpenAI-compatible client). Keys: https://console.groq.com/keys
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # Default: GPT-OSS 120B — Groq production flagship (reasoning, large context).
    # Strong alternative: llama-3.3-70b-versatile
    groq_model: str = "openai/gpt-oss-120b"
    # Cap user message chars for Groq free tier (~8k TPM); dense text uses more tokens per char.
    groq_max_prompt_chars: int = 8000

    # Parallel Search API (required for search) — https://docs.parallel.ai/api-reference/search-beta/search
    parallel_api_key: str = ""
    parallel_beta_header: str = "search-extract-2025-10-10"
    # Keep moderate so Parallel+Groq stays under tier limits; raise via env if your Groq tier allows.
    parallel_max_chars_per_result: int = 3500

    max_search_results: int = 5
    scrape_timeout_s: float = 15.0
    max_chars_per_page: int = 12000


settings = Settings()
