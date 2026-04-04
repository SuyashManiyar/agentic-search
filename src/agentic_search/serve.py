"""Development server: `agentic-serve` or `python -m agentic_search.serve`."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    import uvicorn

    # Parent of package dir = .../src (so `import agentic_search` works)
    src_dir = Path(__file__).resolve().parent.parent
    uvicorn.run(
        "agentic_search.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir=str(src_dir),
        reload_dirs=[str(src_dir)],
    )


if __name__ == "__main__":
    main()
