"""Unit tests for the drission kernel session and tab adapters."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from drission_kernel import DrissionBrowserSession, InvalidTabHandleError, ensure_tab_handle
from drission_kernel import session as session_module


class _FakeRawListener:
    def __init__(self, *, wait_result=None, wait_error: Exception | None = None) -> None:
        self.wait_result = wait_result
        self.wait_error = wait_error
        self.start_calls: list[dict[str, object]] = []
        self.wait_calls: list[dict[str, object]] = []
        self.stop_calls = 0

    def start(self, **kwargs) -> None:
        self.start_calls.append(dict(kwargs))

    def wait(self, **kwargs):
        self.wait_calls.append(dict(kwargs))
        if self.wait_error is not None:
            raise self.wait_error
        return self.wait_result

    def stop(self) -> None:
        self.stop_calls += 1


class _FakeRawTab:
    def __init__(self, name: str, *, listener: _FakeRawListener | None = None) -> None:
        self.name = name
        self.url = "about:blank"
        self.title = "blank"
        self.html = "<html></html>"
        self.listen = listener or _FakeRawListener()
        self.scroll = SimpleNamespace(down=lambda _pixels: None)
        self.states = SimpleNamespace(is_loading=False)
        self.actions = SimpleNamespace(_dr=SimpleNamespace(run=lambda *args, **kwargs: None), modifier=0)
        self.set = SimpleNamespace(cookies=lambda _cookies: None)
        self.get_calls: list[tuple[str, int, int]] = []
        self.run_js_calls: list[str] = []
        self.close_calls = 0

    def get(self, url: str, timeout: int = 10, retry: int = 0):
        self.get_calls.append((url, timeout, retry))
        self.url = url
        self.title = url
        return {"url": url}

    def ele(self, selector: str, timeout: float = 0, index: int = 1):
        return {"selector": selector, "timeout": timeout, "index": index}

    def eles(self, selector: str, timeout: float = 0):
        return [{"selector": selector, "timeout": timeout}]

    def refresh(self) -> None:
        self.refreshed = True

    def run_js(self, script: str):
        self.run_js_calls.append(script)
        return script

    def close(self) -> None:
        self.close_calls += 1


class _FakeBrowser:
    def __init__(self) -> None:
        self.cookies_set = None
        self.closed_tabs: list[str] = []
        self.quit_called = False
        self.get_tab_calls: list[str] = []
        self._tabs: dict[str, _FakeRawTab] = {}
        self._local_storage: dict[str, dict[str, object]] = {}

    def set_cookies(self, cookies) -> None:
        self.cookies_set = cookies

    def get_tab(self, site_name: str) -> _FakeRawTab:
        self.get_tab_calls.append(site_name)
        return self._tabs.setdefault(site_name, _FakeRawTab(site_name))

    def close(self, site_name: str) -> None:
        self.closed_tabs.append(site_name)
        tab = self._tabs.pop(site_name, None)
        if tab is not None:
            tab.close()

    def quit(self) -> None:
        self.quit_called = True
        for tab in list(self._tabs.values()):
            tab.close()
        self._tabs.clear()

    def get_cookies(self, target_domain: str | None = None) -> list[dict[str, object]]:
        cookies = [
            {"name": "alpha", "domain": "alpha.example", "value": "1"},
            {"name": "beta", "domain": "beta.example", "value": "2"},
        ]
        if target_domain is None:
            return cookies
        return [cookie for cookie in cookies if target_domain in str(cookie["domain"])]

    def get_local_storage(self, site_name: str) -> dict[str, object]:
        return dict(self._local_storage.get(site_name, {}))

    def set_local_storage(self, site_name: str, payload: dict[str, object]) -> None:
        self._local_storage[site_name] = dict(payload)


def test_session_close_invalidates_old_handles_and_recreates_fresh_tab() -> None:
    browser = _FakeBrowser()
    session = DrissionBrowserSession(browser=browser)

    first = session.get_tab("alpha")
    first_raw = first.raw
    session.close_tab("alpha")

    with pytest.raises(InvalidTabHandleError):
        first.get("https://alpha.example")

    second = session.get_tab("alpha")

    assert second is not first
    assert browser.closed_tabs == ["alpha"]
    assert second.raw is not first_raw


def test_session_quit_invalidates_handles_and_blocks_future_tab_requests() -> None:
    session = DrissionBrowserSession(browser=_FakeBrowser())
    handle = session.get_tab("alpha")

    session.quit()

    with pytest.raises(InvalidTabHandleError):
        handle.ele("tag:body")
    with pytest.raises(RuntimeError):
        session.get_tab("beta")


def test_listener_wait_stops_listener_after_success() -> None:
    packet = SimpleNamespace(response=SimpleNamespace(body=b"payload"))
    listener = _FakeRawListener(wait_result=packet)
    browser = _FakeBrowser()
    browser._tabs["alpha"] = _FakeRawTab("alpha", listener=listener)
    handle = DrissionBrowserSession(browser=browser).get_tab("alpha")

    handle.listen.start(targets="demo", method="GET")
    result = handle.listen.wait(count=1, timeout=2)

    assert result is packet
    assert listener.start_calls == [{"targets": "demo", "method": "GET"}]
    assert listener.wait_calls == [{"count": 1, "timeout": 2}]
    assert listener.stop_calls == 1


def test_listener_wait_stops_listener_after_exception() -> None:
    listener = _FakeRawListener(wait_error=TimeoutError("timed out"))
    browser = _FakeBrowser()
    browser._tabs["alpha"] = _FakeRawTab("alpha", listener=listener)
    handle = DrissionBrowserSession(browser=browser).get_tab("alpha")

    handle.listen.start(targets="demo")
    with pytest.raises(TimeoutError):
        handle.listen.wait(timeout=1)

    assert listener.stop_calls == 1


def test_ensure_tab_handle_returns_existing_handles_without_wrapping_again() -> None:
    session = DrissionBrowserSession(browser=_FakeBrowser())
    handle = session.get_tab("alpha")

    assert ensure_tab_handle(handle) is handle


class _FakeChromiumOptions:
    def __init__(self) -> None:
        self.arguments: list[str] = []
        self.prefs: dict[str, object] = {}
        self.user_agent = None
        self.proxy = None
        self.download_path = None
        self.user_data_path = None
        self.browser_path = None
        self.headless_value = None

    def headless(self, value: bool):
        self.headless_value = value
        return self

    def set_argument(self, value: str) -> None:
        self.arguments.append(value)

    def set_user_agent(self, value: str) -> None:
        self.user_agent = value

    def set_proxy(self, value: str) -> None:
        self.proxy = value

    def set_pref(self, key: str, value) -> None:
        self.prefs[key] = value

    def set_download_path(self, value) -> None:
        self.download_path = value

    def set_user_data_path(self, value) -> None:
        self.user_data_path = value

    def set_browser_path(self, value) -> None:
        self.browser_path = value


class _FakeChromiumPage:
    def __init__(self, _options: _FakeChromiumOptions) -> None:
        self.tabs_count = 0
        self.created_tabs: list[SimpleNamespace] = []

    def new_tab(self):
        self.tabs_count += 1
        tab = SimpleNamespace(close=lambda: None)
        self.created_tabs.append(tab)
        return tab

    def cookies(self, as_dict: bool = False, all_domains: bool = True):
        _ = as_dict, all_domains
        return []

    def quit(self) -> None:
        return None

    set = SimpleNamespace(cookies=lambda _cookies: None)


def _fake_settings():
    return session_module.BrowserBootstrapConfig(
        user_agent="Mozilla/5.0",
        proxy=None,
        download_path=Path("/tmp/download"),
        user_data_dir=Path("/tmp/user-data"),
        browser_path=Path("/tmp/chrome"),
        language="zh-CN",
    )


def test_chromium_browser_reuses_same_named_tab_for_concurrent_requests(monkeypatch) -> None:
    fake_options = _FakeChromiumOptions()
    monkeypatch.setattr(session_module, "ChromiumOptions", lambda: fake_options)
    monkeypatch.setattr(session_module, "ChromiumPage", _FakeChromiumPage)
    monkeypatch.setattr(session_module, "cleanup_stale_chromium_singleton", lambda *_args, **_kwargs: False)

    browser = session_module.ChromiumBrowser(headless=True, config=_fake_settings())
    results: list[object] = []
    errors: list[Exception] = []

    def _request_tab() -> None:
        try:
            results.append(browser.get_tab("alpha"))
        except Exception as exc:  # pragma: no cover - debug guard for failing red tests
            errors.append(exc)

    first = threading.Thread(target=_request_tab)
    second = threading.Thread(target=_request_tab)
    first.start()
    second.start()
    first.join(timeout=2)
    second.join(timeout=2)

    assert errors == []
    assert len(results) == 2
    assert results[0] is results[1]
    assert len(browser.tabs) == 1
    assert len(browser.page.created_tabs) == 1


def test_chromium_browser_blocks_new_named_tab_until_slot_is_freed(monkeypatch) -> None:
    fake_options = _FakeChromiumOptions()
    monkeypatch.setattr(session_module, "ChromiumOptions", lambda: fake_options)
    monkeypatch.setattr(session_module, "ChromiumPage", _FakeChromiumPage)
    monkeypatch.setattr(session_module, "cleanup_stale_chromium_singleton", lambda *_args, **_kwargs: False)

    browser = session_module.ChromiumBrowser(headless=True, max_tabs=1, config=_fake_settings())
    alpha = browser.get_tab("alpha")
    assert alpha is not None

    result: dict[str, object] = {}

    def _request_beta() -> None:
        result["tab"] = browser.get_tab("beta")

    worker = threading.Thread(target=_request_beta)
    worker.start()
    time.sleep(0.1)
    assert "tab" not in result

    browser.close("alpha")
    worker.join(timeout=2)

    assert result["tab"] is browser.tabs["beta"]
