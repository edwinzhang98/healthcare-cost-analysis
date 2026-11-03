"""Capture a screenshot of every dashboard page for the README.

Requires the dev extras:  uv pip install -r requirements-dev.txt && playwright install chromium
Run from the repo root:   python scripts/screenshots.py
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
PAGES = [("", "01_overview"), ("data-checks", "02_data_checks"), ("national", "03_national"),
         ("benchmarking", "04_benchmarking"), ("penalty", "05_penalty"), ("business-case", "06_business_case"),
         ("recommendations", "07_recommendations")]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.port", str(port),
                             "--server.headless", "true"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                break
            except OSError:
                time.sleep(0.5)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1500}, device_scale_factor=1)
            for path, name in PAGES:
                page.goto(f"http://127.0.0.1:{port}/{path}", wait_until="networkidle")
                page.wait_for_selector("h1", timeout=60_000)
                # wait until the page script has drawn its content (a chart or table) and stopped running
                page.wait_for_selector(".js-plotly-plot, [data-testid='stDataFrame'], [data-testid='stTable']",
                                       timeout=60_000)
                page.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')",
                                       timeout=60_000)
                page.wait_for_timeout(4500)            # let plotly finish drawing
                page.screenshot(path=str(OUT / f"{name}.png"))
                print("saved", OUT / f"{name}.png")
            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=20)


if __name__ == "__main__":
    main()
