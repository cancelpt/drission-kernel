"""Repository-owned browser smoke verification for Docker runtimes."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Iterator

from drission_kernel import BrowserBootstrapConfig, create_browser_session, wait_for_element, wait_for_title

SMOKE_TITLE = "drission-kernel smoke"
SMOKE_HEADING = "browser smoke"
SMOKE_TAB_NAME = "docker-smoke"
_BROWSER_ENV_VAR = "DRISSION_KERNEL_BROWSER_PATH"
_BROWSER_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
)


def resolve_browser_path() -> Path:
    """Resolve the browser binary used for Docker smoke verification."""
    explicit = os.getenv(_BROWSER_ENV_VAR, "").strip()
    if explicit:
        return Path(explicit)

    for candidate in _BROWSER_CANDIDATES:
        resolved = shutil.which(candidate)
        if resolved:
            return Path(resolved)

    raise FileNotFoundError("No supported browser binary found. Set DRISSION_KERNEL_BROWSER_PATH or install chromium.")


def _build_smoke_html() -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{SMOKE_TITLE}</title>
  </head>
  <body>
    <h1>{SMOKE_HEADING}</h1>
  </body>
</html>
"""


def _write_smoke_page(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    page = root / "index.html"
    page.write_text(_build_smoke_html(), encoding="utf-8")
    return page


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        _ = format, args


@contextmanager
def _serve_directory(root: Path) -> Iterator[str]:
    handler = partial(_QuietHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def _run_browser_smoke(browser_path: Path, workspace: Path) -> None:
    site_root = workspace / "site"
    _write_smoke_page(site_root)

    config = BrowserBootstrapConfig(
        browser_path=browser_path,
        download_path=workspace / "downloads",
        user_data_dir=workspace / "chrome-data",
        language="en-US",
    )
    session = None
    try:
        session = create_browser_session(headless=True, config=config)
        tab = session.get_tab(SMOKE_TAB_NAME)
        with _serve_directory(site_root) as url:
            tab.get(url, timeout=10)
            wait_for_title(tab, SMOKE_TITLE, timeout=10)
            heading = wait_for_element(tab, "tag:h1", timeout=10)
            if str(getattr(heading, "text", "")).strip() != SMOKE_HEADING:
                raise AssertionError(f"Expected h1 text {SMOKE_HEADING!r}")
    finally:
        if session is not None:
            session.quit()


def run_browser_smoke(*, browser_path: Path | str | None = None, workspace: Path | str | None = None) -> None:
    """Run the repository-owned headless browser smoke check."""
    resolved_browser = Path(browser_path) if browser_path is not None else resolve_browser_path()
    if workspace is None:
        with tempfile.TemporaryDirectory(prefix="drission-kernel-smoke-") as tmp_dir:
            _run_browser_smoke(resolved_browser, Path(tmp_dir))
        return

    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    _run_browser_smoke(resolved_browser, root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the drission-kernel Docker browser smoke check.")
    parser.add_argument("--browser-path", default=None, help="Explicit browser executable path")
    parser.add_argument("--workspace", default=None, help="Existing workspace directory for smoke artifacts")
    args = parser.parse_args()

    run_browser_smoke(browser_path=args.browser_path, workspace=args.workspace)
    print("Browser smoke verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
