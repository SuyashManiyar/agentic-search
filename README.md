# Agentic Search

A small **agentic search** pipeline for the **CIIR Agentic Search Challenge**: given a natural-language **topic**, it searches the web, gathers page text, and uses an LLM to produce a **structured table of entities** (JSON) where fields are backed by **citations** (source URL + short quote).

## Challenge alignment

| Requirement | How this project satisfies it |
|-------------|-------------------------------|
| Topic query in | CLI (`python -m agentic_search "…"`), `POST /search` JSON body, or browser UI |
| Web search | [Parallel Search API](https://docs.parallel.ai/api-reference/search-beta/search) (`POST /v1beta/search`) |
| Scrape / process pages | Parallel **excerpts** when provided; otherwise `httpx` fetch + BeautifulSoup/lxml text extraction |
| LLM extraction | [Groq](https://console.groq.com/) via OpenAI-compatible chat completions + JSON mode |
| Structured table | JSON array `entities[]` with `name`, `summary`, `attributes`, `citations[]` |
| Traceability | Each citation ties a **field** to a **URL** and **verbatim quote** (prompt instructs the model to ground claims) |

## Architecture

```
topic string
    → Parallel Search (objective + queries, ranked results + long excerpts)
    → for each result: use excerpt text OR scrape URL in parallel
    → cap combined text for Groq TPM limits
    → Groq: structured JSON { entities: [...] }
    → return JSON (CLI stdout or HTTP)
```

**Modules** (under `src/agentic_search/`):

- `config.py` — settings from environment / `.env` (project root, not cwd)
- `search.py` — Parallel API client
- `scrape.py` — HTML → plain text for URLs without usable excerpts
- `extract.py` — prompt assembly, prompt-size cap, Groq call, Pydantic validation
- `pipeline.py` — orchestration (`asyncio.gather` for fetches)
- `api.py` — FastAPI + minimal HTML UI
- `__main__.py` — CLI
- `serve.py` — dev server entry (`agentic-serve`)

## Approach

1. **Retrieval**  
   We call Parallel with an **objective** derived from the user topic and a **keyword query** list (`[topic]`). Parallel returns ranked results with **title**, **URL**, and **excerpts** tuned for downstream LLM use. That reduces reliance on brittle scraping when excerpts are present.

2. **Content assembly**  
   For each hit, if excerpts exist we treat them as the “page content” for extraction; if not, we **fetch the URL** and strip boilerplate (scripts, nav, etc.) to text. All pairs `(url, text)` are passed to the model with explicit `[SOURCE_URL: …]` markers so URLs in citations can match real inputs.

3. **Extraction**  
   A single chat completion asks for strict JSON: a list of entities with attributes and a **citations** array. Each citation names which field it supports (`name`, `summary`, or `attributes.<key>`), the **url**, and a **short quote** from that source. We use **`response_format: json_object`** where supported to improve parseability, then validate with Pydantic.

4. **Serving**  
   **FastAPI** exposes `POST /search` and a tiny **single-page UI** for demos. The CLI prints pretty-printed JSON for scripts and debugging.

## Design decisions

- **Parallel only for search**  
  We removed generic search fallbacks so behavior is **predictable** and **high-signal** for grading: one vendor, one response shape, strong excerpts. The trade-off is a **hard dependency** on `PARALLEL_API_KEY`.

- **Groq for inference**  
  Fast, OpenAI-compatible API, good for iterative development. Default model is **`openai/gpt-oss-120b`**; you can switch to e.g. `llama-3.3-70b-versatile` via `GROQ_MODEL`.

- **Prompt size cap (`GROQ_MAX_PROMPT_CHARS`)**  
  Groq **free tier** enforces tight **TPM / request size** limits. Unbounded Parallel excerpts can exceed those limits (HTTP 413). We **truncate** the user message in order: include full sources until the budget is exhausted, then truncate the next excerpt. Trade-off: **fewer tokens** vs **multi-source** context; raise the cap if you upgrade Groq.

- **Defaults tuned for free tier**  
  Moderate `PARALLEL_MAX_CHARS_PER_RESULT`, `max_search_results` (5), and `GROQ_MAX_PROMPT_CHARS` (8000) to stay under typical limits without manual tuning.

- **`.env` resolved from project root**  
  Settings load `.env` next to `pyproject.toml`, so commands work from different working directories as long as the package is installed.

- **`python -m pip install -e .`**  
  On macOS, plain `pip` can target a **different Python** than `python` (e.g. system vs Conda), causing `No module named agentic_search`. Installing with **`python -m pip`** avoids that class of bug.

## Known limitations

- **LLM fidelity** — The model can still **hallucinate** or cite poorly; citations are an **audit trail**, not a guarantee. Important facts should be checked against the linked pages.
- **Single search provider** — No fallback if Parallel is down or the key is invalid; the run fails fast with a clear error.
- **Scraping** — Many sites **block bots** or return empty bodies; excerpt-less results may contribute little text. No robots.txt respect, rate limiting, or distributed crawl.
- **No caching** — Repeated queries re-hit Parallel and Groq; no deduplication of URLs across runs.
- **Latency & cost** — Parallel search can be **slow** (large timeout); Groq and Parallel are **metered** services.
- **Citation quality** — Short or generic quotes (e.g. domain-only) can appear if the model is under-constrained; the prompt could be tightened further for production.
- **Live demo** — Not deployed by default; hosting on a free tier (Render, Railway, Fly.io, etc.) is optional for submission (see challenge text).

## Setup instructions

### Prerequisites

- **Python 3.10+**
- Accounts / keys: **Parallel** (search), **Groq** (LLM)

### 1. Clone and enter the repo

```bash
cd /path/to/agent
```

### 2. Environment (Conda recommended)

```bash
conda env create -f environment.yml
conda activate agentic-search
python -m pip install -e .
```

**Or** use a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e .
```

### 3. Configure secrets

```bash
cp .env.example .env
```

Edit `.env` (single-line values, no broken quotes):

| Variable | Required | Description |
|----------|----------|-------------|
| `PARALLEL_API_KEY` | Yes | Parallel Search API key |
| `GROQ_API_KEY` | Yes | Groq API key |
| `GROQ_BASE_URL` | No | Default `https://api.groq.com/openai/v1` |
| `GROQ_MODEL` | No | Default `openai/gpt-oss-120b` |
| `GROQ_MAX_PROMPT_CHARS` | No | Default `8000` — lower if 413/TPM errors persist |
| `PARALLEL_BETA_HEADER` | No | Default `search-extract-2025-10-10`; empty to omit |
| `PARALLEL_MAX_CHARS_PER_RESULT` | No | Default `3500` |

Never commit `.env` or real keys (`.gitignore` includes `.env`).

### 4. Run

**CLI** (JSON to stdout):

```bash
python -m agentic_search "AI startups in healthcare"
```

**HTTP server** (UI + API):

```bash
agentic-serve
# or: uvicorn agentic_search.api:app --reload --app-dir src
```

- UI: http://127.0.0.1:8000  
- Health: `GET /health`  
- Search: `POST /search` with body `{"topic":"your query"}`

### 5. Optional: public URL

For a live demo, deploy the same Uvicorn app on a free-tier host, set the same env vars in the platform dashboard, bind to `0.0.0.0`, and use the platform’s `PORT` if required.

## Demo (PDF)

A **static demo** of the project (e.g. web UI, example query, and sample output) is included in **`Agentic_search_demo.pdf`** at the repository root. Open that file for a walkthrough when a hosted URL is not available.

## Submission (CIIR)

- **Email:** `csamarinas@umass.edu`  
- **Subject line (exact):** `CIIR challenge submission`  
- **Include:** link to a **public GitHub** repository containing this code.  
- **Demo:** see **`Agentic_search_demo.pdf`** in the repo; a **live demo** URL on a free-tier host is optional but encouraged.

## License

Provided as challenge submission code; add a license file if you open-source the repo publicly.
