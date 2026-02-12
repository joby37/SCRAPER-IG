#!/usr/bin/env python3
"""Reliable Playwright scraper for OEC pages.

Usage:
  python oec_playwright_scraper.py --url https://oec.world/en/profile/country/usa
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape data from OEC pages with Playwright")
    parser.add_argument(
        "--url",
        default="https://oec.world/en/profile/country/usa",
        help="OEC URL to scrape",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run browser in non-headless mode for local debugging",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=45000,
        help="Default timeout for Playwright operations",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Navigation retry attempts",
    )
    parser.add_argument(
        "--output",
        default="oec_result.json",
        help="Path to write extracted JSON",
    )
    parser.add_argument(
        "--screenshot",
        default="oec_debug.png",
        help="Path to write screenshot",
    )
    return parser.parse_args()


def safe_texts(page: Page, selector: str, limit: int = 20) -> list[str]:
    texts: list[str] = []
    loc = page.locator(selector)
    count = min(loc.count(), limit)
    for i in range(count):
        text = loc.nth(i).inner_text(timeout=3000).strip()
        if text:
            texts.append(" ".join(text.split()))
    return texts


def navigate_with_retry(page: Page, url: str, max_retries: int) -> None:
    from playwright.sync_api import TimeoutError

    for attempt in range(1, max_retries + 1):
        try:
            page.goto(url, wait_until="domcontentloaded")
            # OEC is a JS-heavy SPA; network can stay busy, so we avoid hard reliance on networkidle.
            page.wait_for_timeout(2000)
            page.locator("main, #root, body").first.wait_for(state="visible", timeout=10000)
            return
        except TimeoutError:
            if attempt == max_retries:
                raise
            backoff = attempt * 2
            print(f"[warn] attempt {attempt}/{max_retries} failed; retrying in {backoff}s", file=sys.stderr)
            time.sleep(backoff)


def extract_data(page: Page, url: str) -> dict[str, Any]:
    title = page.title()
    h1 = page.locator("h1").first.inner_text(timeout=5000).strip() if page.locator("h1").count() else ""

    # Common text containers on OEC pages.
    key_blocks = safe_texts(page, "main section h2, main section h3, main [class*='title']", limit=30)
    stat_blocks = safe_texts(page, "main [class*='value'], main [class*='stat'], main [class*='number']", limit=30)

    return {
        "url": url,
        "title": title,
        "h1": h1,
        "headings": key_blocks,
        "stats": stat_blocks,
        "scraped_at_epoch": int(time.time()),
    }


def run(browser: Browser, args: argparse.Namespace) -> dict[str, Any]:
    context = browser.new_context(
        viewport={"width": 1440, "height": 2200},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        timezone_id="UTC",
    )
    page = context.new_page()
    page.set_default_timeout(args.timeout_ms)

    # Helps debug intermittent runtime errors on dynamic pages.
    page.on("console", lambda msg: print(f"[browser:{msg.type}] {msg.text}", file=sys.stderr))
    page.on("pageerror", lambda err: print(f"[pageerror] {err}", file=sys.stderr))

    navigate_with_retry(page, args.url, args.max_retries)
    data = extract_data(page, args.url)

    screenshot_path = Path(args.screenshot)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(screenshot_path), full_page=True)

    context.close()
    return data


def main() -> int:
    args = parse_args()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print(
            "Playwright is not installed. Install it with: pip install playwright && python -m playwright install chromium",
            file=sys.stderr,
        )
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        try:
            data = run(browser, args)
        finally:
            browser.close()

    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
