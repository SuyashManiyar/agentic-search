"""CLI: python -m agentic_search \"your topic\""""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from agentic_search.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    p = argparse.ArgumentParser(description="Agentic search: topic → structured table + citations")
    p.add_argument("topic", nargs="?", help="Search topic")
    p.add_argument("-o", "--output", help="Write JSON to file")
    args = p.parse_args()
    topic = args.topic or (sys.stdin.read().strip() if not sys.stdin.isatty() else "")
    if not topic:
        p.print_help()
        sys.exit(1)

    try:
        result = asyncio.run(run_pipeline(topic))
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    out = json.dumps(result.model_dump(), indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
