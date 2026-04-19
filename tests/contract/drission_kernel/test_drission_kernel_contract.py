"""Contract tests for the extracted drission kernel session surface."""

from __future__ import annotations

from types import SimpleNamespace

from drission_kernel import BrowserSession, DrissionBrowserSession, TabHandle, create_browser_session


class _FakeRawListener:
    def start(self, **kwargs) -> None:
        self.started = kwargs

    def wait(self, **kwargs):
        self.waited = kwargs
        return SimpleNamespace(response=SimpleNamespace(body=b"payload"))

    def stop(self) -> None:
        self.stopped = True


class _FakeRawTab:
    def __init__(self, name: str) -> None:
        self.name = name
        self.url = "about:blank"
        self.title = "blank"
        self.html = "<html></html>"
        self.listen = _FakeRawListener()
        self.scroll = SimpleNamespace(down=lambda _pixels: None)
        self.states = SimpleNamespace(is_loading=False)
        self.set = SimpleNamespace(cookies=lambda _cookies: None)

    def get(self, url: str, timeout: int = 10, retry: int = 0):
        self.url = url
        self.title = url
        return {"url": url, "timeout": timeout, "retry": retry}

    def ele(self, selector: str, timeout: float = 0, index: int = 1):
        return {"selector": selector, "timeout": timeout, "index": index}

    def eles(self, selector: str, timeout: float = 0):
        return [{"selector": selector, "timeout": timeout}]

    def refresh(self) -> None:
        self.refreshed = True

    def run_js(self, script: str):
        self.last_script = script
        return script


class _FakeBrowser:
    def __init__(self) -> None:
        self.cookies_set = None
        self.closed_tabs: list[str] = []
        self.quit_called = False
        self._tabs: dict[str, _FakeRawTab] = {}
        self._local_storage: dict[str, dict[str, object]] = {}

    def set_cookies(self, cookies) -> None:
        self.cookies_set = cookies

    def get_tab(self, site_name: str) -> _FakeRawTab:
        return self._tabs.setdefault(site_name, _FakeRawTab(site_name))

    def close(self, site_name: str) -> None:
        self.closed_tabs.append(site_name)
        self._tabs.pop(site_name, None)

    def quit(self) -> None:
        self.quit_called = True

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


def test_drission_session_is_structural_browser_session_and_returns_tab_handles() -> None:
    browser = _FakeBrowser()
    session = DrissionBrowserSession(browser=browser)

    handle = session.get_tab("alpha")

    assert isinstance(session, BrowserSession)
    assert isinstance(handle, TabHandle)
    assert handle.raw is browser.get_tab("alpha")


def test_drission_session_reuses_named_tab_handles_until_closed() -> None:
    session = DrissionBrowserSession(browser=_FakeBrowser())

    first = session.get_tab("alpha")
    second = session.get_tab("alpha")

    assert first is second


def test_create_browser_session_wraps_injected_browser() -> None:
    browser = _FakeBrowser()

    session = create_browser_session(browser=browser)

    assert isinstance(session, DrissionBrowserSession)
    assert session.raw is browser
