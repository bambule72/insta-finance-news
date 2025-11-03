#!/usr/bin/env python3
"""Small helper to run the scraper and print/save results.

Usage:
  python scripts/print_scrape.py [--out file.json]

This prints the scraped items to stdout as JSON and optionally writes to a file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.news_scraper.scraper import get_latest_news, get_latest_sec_form_144
from src.news_scraper.logger import setup_logger


logger = setup_logger("cli.print_scrape")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", "-o", help="Write results to this JSON file", default=None)
    args = p.parse_args()

    logger.info("Running SEC Form 144 scraper")
    # Use the SEC Form 144 flow to get structured filing items
    items = get_latest_sec_form_144(limit=20)
    print(json.dumps(items, indent=2, ensure_ascii=False))

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(items, indent=2, ensure_ascii=False))
        logger.info("Wrote %d items to %s", len(items), out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
