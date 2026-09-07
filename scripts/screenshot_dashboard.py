"""Screenshot every dashboard page at several widths, for visual review.

The AppTest suite proves the pages execute and what elements they contain.  It
says nothing about how they look, and the dashboard's whole purpose is to be
read.  This script closes that gap: it starts the app, walks the pages, and
writes PNGs to docs/screenshots/.

Usage:
    python scripts/screenshot_dashboard.py [--width 1440] [--keep-server]

Requires playwright and its chromium build:
    pip install playwright && python -m playwright install chromium
"""

import argparse
import socket
import subprocess
import sys
import time
import sys as _sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_sys.path.insert(0, str(_PROJECT_ROOT))
_OUTPUT_DIR = _PROJECT_ROOT / "docs" / "screenshots"

#: Desktop, tablet and phone.  The phone width is where the fixed pixel chart
#: margins are most likely to crush the plot area.
#:
#: The heights are deliberately far taller than a real screen.  Streamlit
#: renders into its own scrolling container, so Playwright's ``full_page``
#: screenshot captures only what fits the viewport and silently truncates the
#: rest — every capture before 2026-09-07 showed just the top of each page.
VIEWPORTS: dict[str, tuple[int, int]] = {
    "desktop": (1440, 3400),
    "tablet": (900, 3600),
    "phone": (390, 4200),
}

#: Streamlit derives a page's URL slug from its filename with the numeric
#: ordering prefix stripped, so pages/01_Riksoversikt.py is served at
#: /Riksoversikt.  Getting this wrong does not error: Streamlit shows a
#: "Page not found" modal over the main page, which screenshots as a
#: plausible-looking landing page.
PAGES: dict[str, str] = {
    "01-startsida": "/",
    "02-riksoversikt": "/Riksoversikt",
    "03-kommunjamforelse": "/Kommunjamforelse",
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


def _wait_for(url: str, timeout: float = 90.0) -> None:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    raise TimeoutError(f"Streamlit did not answer on {url} within {timeout:.0f}s")


def capture(port: int, viewports: dict[str, tuple[int, int]]) -> list[Path]:
    """Screenshot every page at every viewport, plus each map layer."""
    from playwright.sync_api import sync_playwright

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, (width, height) in viewports.items():
            page = browser.new_page(viewport={"width": width, "height": height})
            for page_name, path in PAGES.items():
                page.goto(f"http://localhost:{port}{path}", wait_until="networkidle")
                # Streamlit renders over a websocket after load; the skeleton is
                # gone once the app has actually drawn.
                page.wait_for_timeout(6000)
                target = _OUTPUT_DIR / f"{page_name}-{vp_name}.png"
                page.screenshot(path=str(target), full_page=True)
                written.append(target)
                print(f"  wrote {target.relative_to(_PROJECT_ROOT)}")

            # Map layers, desktop only: the toggle is the same on every width.
            if vp_name == "desktop":
                page.goto(
                    f"http://localhost:{port}{PAGES['02-riksoversikt']}",
                    wait_until="networkidle",
                )
                page.wait_for_timeout(6000)
                # Streamlit hides the radio <input> and styles its label, so the
                # input itself is never clickable: click the visible label text.
                from src.ui.choropleth import MAP_LAYERS

                for layer, spec in MAP_LAYERS.items():
                    page.get_by_text(spec.label, exact=True).first.click()
                    page.wait_for_timeout(5000)
                    target = _OUTPUT_DIR / f"04-map-{layer}.png"
                    page.screenshot(path=str(target), full_page=False)
                    written.append(target)
                    print(f"  wrote {target.relative_to(_PROJECT_ROOT)}")
            page.close()
        browser.close()
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Capture a single width instead of all three.",
    )
    parser.add_argument(
        "--keep-server",
        action="store_true",
        help="Leave Streamlit running after capture.",
    )
    args = parser.parse_args()

    viewports = VIEWPORTS
    if args.width:
        # Tall for the same reason the defaults are: Streamlit's scroll
        # container defeats full_page, so height must be generous.
        viewports = {f"w{args.width}": (args.width, 3400)}

    port = _free_port()
    print(f"Starting Streamlit on port {port} …")
    server = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.headless", "true",
            "--server.port", str(port),
            "--browser.gatherUsageStats", "false",
        ],
        cwd=_PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for(f"http://localhost:{port}/")
        print("Capturing …")
        written = capture(port, viewports)
        print(f"\n{len(written)} screenshots in {_OUTPUT_DIR}")
    finally:
        if not args.keep_server:
            server.terminate()
            server.wait(timeout=20)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
