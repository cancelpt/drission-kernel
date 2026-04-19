"""Extended contract tests for BrowserSession protocol behavior."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from drission_kernel import BrowserSession  # noqa: E402


class LegacyMinimalBrowserStub:
    """Legacy stub shape: only cookie setup and tab acquisition."""

    def set_cookies(self, cookies: Any) -> None:
        self.cookies = cookies

    def get_tab(self, site_name: str) -> dict[str, str]:
        return {"id": site_name}


class ExtendedBrowserStub:
    """Stub implementing expected BrowserSession behavior."""

    def __init__(self) -> None:
        self._cookies: list[dict[str, Any]] = []
        self._local_storage: dict[str, dict[str, Any]] = {}
        self._tabs: dict[str, dict[str, str]] = {}

    @property
    def raw(self):
        return self

    def set_cookies(self, cookies: Any) -> None:
        if isinstance(cookies, list):
            self._cookies = cookies

    def get_tab(self, site_name: str) -> dict[str, str]:
        return self._tabs.setdefault(site_name, {"id": site_name})

    def close_tab(self, site_name: str) -> None:
        self._tabs.pop(site_name, None)

    def quit(self) -> None:
        self._tabs.clear()

    def get_cookies(self, target_domain: str | None = None) -> list[dict[str, Any]]:
        if target_domain is None:
            return list(self._cookies)
        return [cookie for cookie in self._cookies if target_domain in str(cookie.get("domain", ""))]

    def get_local_storage(self, site_name: str) -> dict[str, Any]:
        return dict(self._local_storage.get(site_name, {}))

    def set_local_storage(self, site_name: str, payload: dict[str, Any]) -> None:
        self._local_storage[site_name] = dict(payload)


def test_browser_session_requires_cookie_query_and_local_storage_methods() -> None:
    assert not isinstance(LegacyMinimalBrowserStub(), BrowserSession)


def test_extended_browser_stub_is_structural_browser_session() -> None:
    assert isinstance(ExtendedBrowserStub(), BrowserSession)


def test_extended_browser_stub_cookies_and_local_storage_behavior() -> None:
    stub = ExtendedBrowserStub()
    cookies = [
        {"name": "sid", "domain": "alpha.example.com", "value": "1"},
        {"name": "tid", "domain": "beta.example.com", "value": "2"},
    ]

    stub.set_cookies(cookies)
    stub.set_local_storage("alpha", {"token": "abc", "mode": "safe"})

    assert stub.get_cookies() == cookies
    assert stub.get_cookies(target_domain="alpha.example.com") == [cookies[0]]
    assert stub.get_local_storage("alpha") == {"token": "abc", "mode": "safe"}
