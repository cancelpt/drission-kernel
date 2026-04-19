"""Contract tests for browser session adapter and anti-bot migration."""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from drission_kernel import BrowserSession, DrissionBrowserSession, create_browser_session
from drission_kernel.anti_bot import (
    auto_bypass,
    bypass_cloudflare,
    bypass_cloudflare_component,
    bypass_ctlc,
    random_click,
)


class FakeLegacyBrowser:
    """Fake Chromium-like browser for adapter contract verification."""

    def __init__(self) -> None:
        self.cookies_set = None
        self.tabs = {"demo": {"id": "tab-demo"}}
        self.closed_tabs: list[str] = []
        self.quit_called = False
        self.local_storage: dict[str, dict[str, object]] = {}

    def set_cookies(self, cookies):
        self.cookies_set = cookies

    def get_tab(self, site_name):
        return self.tabs.setdefault(site_name, {"id": site_name})

    @property
    def raw(self):
        return self

    def close_tab(self, site_name):
        self.closed_tabs.append(site_name)
        self.tabs.pop(site_name, None)

    def quit(self):
        self.quit_called = True

    def get_cookies(self, target_domain=None):
        _ = target_domain
        return []

    def get_local_storage(self, site_name):
        return dict(self.local_storage.get(site_name, {}))

    def set_local_storage(self, site_name, payload):
        self.local_storage[site_name] = dict(payload)


def test_drission_session_delegates_required_browser_protocol_methods() -> None:
    fake_browser = FakeLegacyBrowser()
    session = DrissionBrowserSession(browser=fake_browser)

    session.set_cookies([{"name": "n", "value": "v"}])
    tab = session.get_tab("alpha")

    assert isinstance(session, BrowserSession)
    assert fake_browser.cookies_set == [{"name": "n", "value": "v"}]
    assert tab.raw == {"id": "alpha"}


def test_create_browser_session_uses_adapter_and_allows_browser_injection() -> None:
    fake_browser = FakeLegacyBrowser()
    session = create_browser_session(browser=fake_browser)

    assert isinstance(session, DrissionBrowserSession)
    assert session.raw is fake_browser


def test_anti_bot_module_exposes_required_helpers() -> None:
    assert callable(auto_bypass)
    assert callable(bypass_cloudflare)
    assert callable(bypass_cloudflare_component)
    assert callable(bypass_ctlc)
    assert callable(random_click)
