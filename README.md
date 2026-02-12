# SCRAPER-IG

Playwright-based scraper for OEC pages.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install playwright
python -m playwright install chromium
```

## Run

```bash
source .venv/bin/activate
python oec_playwright_scraper.py \
  --url "https://oec.world/en/profile/country/usa" \
  --output oec_result.json \
  --screenshot oec_debug.png
```

## Verify it works

```bash
python oec_playwright_scraper.py --help
python oec_playwright_scraper.py --url "https://oec.world/en/profile/country/usa"
cat oec_result.json
```

You should see:
- a JSON file at `oec_result.json`
- a screenshot at `oec_debug.png`

## Common issue

If you get `Playwright is not installed`, run:

```bash
pip install playwright
python -m playwright install chromium
```

## Why this version is more stable

- Uses retry logic for initial navigation.
- Avoids strict `networkidle` dependence (common failure on SPA analytics-heavy pages).
- Waits for visible root/main containers before extraction.
- Captures browser console and page runtime errors to stderr for debugging.
