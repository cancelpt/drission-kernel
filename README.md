[简体中文](README.zh-CN.md)

# drission-kernel

[![CI](https://github.com/cancelpt/drission-kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/cancelpt/drission-kernel/actions/workflows/ci.yml)

`drission-kernel` is a reusable browser automation package built on top of DrissionPage. It focuses on Chromium session bootstrap, named tab reuse, shared wait helpers, and anti-bot primitives for higher-level automation projects.

## What It Provides

- Browser bootstrap through `BrowserBootstrapConfig` and `create_browser_session()`
- Named tab reuse through `BrowserSession.get_tab(site_name)`
- Lifecycle-safe tab handles that are invalidated after `close_tab()` or `quit()`
- Session-level cookie and local storage helpers
- Shared wait helpers such as `wait_for_element()`, `wait_for_title()`, and `url_contains()`
- Anti-bot helpers in `drission_kernel.anti_bot` for SafeLine and Cloudflare challenge flows

## Where It Fits

- Shared browser session infrastructure for higher-level automation flows
- Projects that want to build business logic on top of a stable DrissionPage-based session layer
- Workloads that benefit from named tabs, cookie and local storage helpers, and reusable anti-bot primitives
- Teams that prefer to keep orchestration, parsing, and domain rules in upper layers

## Installation

Requirements:

- Python 3.11+
- A Chrome or Chromium binary available to DrissionPage

Install from the repository root:

```bash
pip install .
```

If DrissionPage cannot detect your browser automatically, set `browser_path` in `BrowserBootstrapConfig`.

## Quick Start

```python
from drission_kernel import (
    BrowserBootstrapConfig,
    create_browser_session,
    url_contains,
    wait_for_element,
)

config = BrowserBootstrapConfig(
    browser_path="/path/to/chrome",  # Optional if DrissionPage can detect it
    download_path="/tmp/drission-kernel/downloads",
    user_data_dir="/tmp/drission-kernel/profile",
    language="en-US",
)

session = create_browser_session(headless=True, config=config)

try:
    tab = session.get_tab("example")
    tab.get("https://example.com", timeout=10)

    if url_contains(tab, "example.com", timeout=5):
        heading = wait_for_element(tab, "tag:h1", timeout=10)
        print(heading.text)

    session.set_local_storage("example", {"mode": "demo"})
    print(session.get_local_storage("example"))
    print(session.get_cookies())
finally:
    session.quit()
```

Named tabs are reused by logical name. Calling `session.get_tab("example")` again returns the same handle until that tab is closed or the session is shut down.

## API Overview

### Session Bootstrap

- `BrowserBootstrapConfig`: configure user agent, proxy, download path, user data directory, browser path, and browser language
- `create_browser_session(browser=None, headless=False, config=None)`: create a `DrissionBrowserSession` around either a new Chromium browser or an injected browser implementation

### Session Operations

- `get_tab(site_name)`: return a stable named tab handle
- `close_tab(site_name)`: close one named tab and invalidate previously issued handles for that name
- `set_cookies(cookies)` / `get_cookies(target_domain=None)`: write and query cookies
- `set_local_storage(site_name, payload)` / `get_local_storage(site_name)`: write and read local storage for a named tab context
- `quit()`: close the full browser session and invalidate all outstanding tab handles

### Tab and Listener Operations

- Tab handles expose `get()`, `ele()`, `eles()`, `refresh()`, and `run_js()`
- Tab handles also expose `url`, `title`, `html`, and `raw` for the wrapped page state
- `tab.listen.start(...)`, `tab.listen.wait(...)`, and `tab.listen.stop()` provide bounded network-listener behavior

### Wait Helpers

- `wait_for_element(tab, selector, timeout=10, index=1)`
- `wait_for_title(tab, expected_title, timeout=10)`
- `url_contains(tab, expected_url, timeout=0.2)`

### Anti-Bot Helpers

Import these from `drission_kernel.anti_bot`:

- `auto_bypass(page)`
- `bypass_ctlc(page)` for SafeLine / LeiChi flows
- `bypass_cloudflare(page)`
- `bypass_cloudflare_component(page, ...)`
- `random_click(page, x, y)`

### Protocol Contracts

- `BrowserSession`, `TabHandle`, and `ListenerHandle` are available if you want to type-check or adapt alternate browser implementations

## Development and Verification

Install in editable mode with test and lint dependencies:

```bash
pip install -e .[test,lint]
```

Install local commit hooks:

```bash
pre-commit install
```

Run hook checks across the repository:

```bash
pre-commit run --all-files
```

Run the test suite:

```bash
pytest -q
```

Run Docker-based package verification:

```bash
docker build -t drission-kernel:test .
docker run --rm drission-kernel:test
```

The container installs Chromium on top of `python:3.11-slim`, runs a headless local-page browser smoke check, and then executes `pytest -q`.

## License

This repository is released under the MIT License. See `LICENSE` for the full text.

The current runtime dependency window is `DrissionPage~=4.0.4.21`. The `4.0.4.25` PyPI distribution in that range declares BSD terms and ships a BSD 3-Clause license file, which is compatible with publishing this repository under MIT.

If you widen that dependency range in the future, re-check upstream licensing before release.

Development tooling also includes `pylint`, which is GPL-2.0-or-later. In this project it is used as a local and CI lint tool, not a runtime dependency of the published package.
