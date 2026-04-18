#!/usr/bin/env python3
"""Capture dashboard preview screenshots via headless Chromium.

Logs into the local demo Grafana, opens each dashboard in kiosk-tv mode
(hides sidebar but keeps the dashboard title bar), waits for panels to
render, and writes a PNG to docs/screenshots/. Designed to be run against
the demo/docker-compose.yaml stack after seeding events with
scripts/seed-events.py.

Requires:
    pip install playwright
    playwright install chromium
"""
from __future__ import annotations

import os
import pathlib
import sys
from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "docs" / "screenshots"

GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
# Expected defaults: seeder reads the same .env file.
_ENV = REPO_ROOT / "demo" / ".env"
_pw_from_env = ""
if _ENV.is_file():
    for line in _ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("GRAFANA_ADMIN_PASSWORD="):
            _pw_from_env = line.split("=", 1)[1].strip()
            break
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", _pw_from_env or "admin")

DASHBOARDS = [
    ("ves-nrcell-du-overview.png", "ves-nrcell-du"),
    ("ves-nrcell-cu-overview.png", "ves-nrcell-cu"),
]

VIEWPORT = {"width": 1920, "height": 1200}
PANEL_RENDER_GRACE_MS = 5000  # Grafana staggers panel loads; give them time.

# CSS to hide Grafana 12's left mega-menu and collapse the top bar so
# the dashboard gets the full viewport width. `?kiosk=tv` in the URL
# was unreliable in 12.2 -- CSS is deterministic.
_HIDE_CHROME_CSS = """
[data-testid="data-testid Nav toggle"],
[data-testid="navbarroot"],
[data-testid="data-testid navigation mega-menu"],
nav[aria-label="Navigation"],
aside,
ul[role="tablist"] {
  display: none !important;
}
main[role="main"] {
  margin-left: 0 !important;
  padding-left: 0 !important;
}
"""


def _login(page, base_url: str, user: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="networkidle")
    page.fill('input[name="user"]', user)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/**", timeout=10_000)
    # Grafana's "change your password" prompt -- skip if present.
    try:
        page.click('a[href="/?forceLogin="], button:has-text("Skip")', timeout=2_500)
    except Exception:
        pass


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"grafana: {GRAFANA_URL}  user: {GRAFANA_USER}  pw: ({len(GRAFANA_PASSWORD)}ch)")
    print(f"output:  {OUT_DIR}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = context.new_page()

        _login(page, GRAFANA_URL, GRAFANA_USER, GRAFANA_PASSWORD)

        for filename, uid in DASHBOARDS:
            url = f"{GRAFANA_URL}/d/{uid}?kiosk&refresh=off"
            print(f"capturing {url}")
            page.goto(url, wait_until="networkidle", timeout=20_000)
            # Force nav chrome away even if kiosk URL param didn't take
            # (behaviour varies between Grafana 11/12 minor versions).
            page.add_style_tag(content=_HIDE_CHROME_CSS)
            page.wait_for_timeout(PANEL_RENDER_GRACE_MS)
            page.wait_for_load_state("networkidle", timeout=10_000)

            out_path = OUT_DIR / filename
            page.screenshot(path=str(out_path), full_page=False)
            print(f"  wrote {out_path} ({out_path.stat().st_size // 1024} KiB)")

        browser.close()

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
