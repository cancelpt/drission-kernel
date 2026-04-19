"""Tests for browser language option wiring in Chromium bootstrap."""

from __future__ import annotations

from types import SimpleNamespace

from drission_kernel import session as chrome


class _FakeChromiumOptions:
    def __init__(self) -> None:
        self.arguments: list[str] = []
        self.prefs: dict[str, object] = {}
        self.download_path = None
        self.user_data_path = None
        self.browser_path = None
        self.proxy = None
        self.user_agent = None
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
    def __init__(self, options: _FakeChromiumOptions) -> None:
        self.options = options
        self.tabs_count = 0

    def new_tab(self):
        return SimpleNamespace()


def _build_config(language: str) -> chrome.BrowserBootstrapConfig:
    return chrome.BrowserBootstrapConfig(
        user_agent="Mozilla/5.0",
        proxy=None,
        download_path="/tmp/download",
        user_data_dir="/tmp/user-data",
        browser_path="/tmp/chrome",
        language=language,
    )


def test_chromium_browser_sets_default_zh_cn_language(monkeypatch) -> None:
    fake_options = _FakeChromiumOptions()
    monkeypatch.setattr(chrome, "ChromiumOptions", lambda: fake_options)
    monkeypatch.setattr(chrome, "ChromiumPage", _FakeChromiumPage)
    monkeypatch.setattr(chrome, "cleanup_stale_chromium_singleton", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(chrome.ChromiumBrowser, "_ChromiumBrowser__instance", None)

    chrome.ChromiumBrowser(headless=True, config=_build_config("zh-CN"))

    assert "--lang=zh-CN" in fake_options.arguments
    assert fake_options.prefs["intl.accept_languages"] == "zh-CN,zh"
    assert fake_options.prefs["intl.selected_languages"] == "zh-CN,zh"


def test_chromium_browser_uses_custom_language(monkeypatch) -> None:
    fake_options = _FakeChromiumOptions()
    monkeypatch.setattr(chrome, "ChromiumOptions", lambda: fake_options)
    monkeypatch.setattr(chrome, "ChromiumPage", _FakeChromiumPage)
    monkeypatch.setattr(chrome, "cleanup_stale_chromium_singleton", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(chrome.ChromiumBrowser, "_ChromiumBrowser__instance", None)

    chrome.ChromiumBrowser(headless=True, config=_build_config("en-US"))

    assert "--lang=en-US" in fake_options.arguments
    assert fake_options.prefs["intl.accept_languages"] == "en-US,en"
    assert fake_options.prefs["intl.selected_languages"] == "en-US,en"


def test_chromium_browser_adds_container_safe_launch_args(monkeypatch) -> None:
    fake_options = _FakeChromiumOptions()
    monkeypatch.setattr(chrome, "ChromiumOptions", lambda: fake_options)
    monkeypatch.setattr(chrome, "ChromiumPage", _FakeChromiumPage)
    monkeypatch.setattr(chrome, "cleanup_stale_chromium_singleton", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(chrome.ChromiumBrowser, "_ChromiumBrowser__instance", None)

    chrome.ChromiumBrowser(headless=True, config=_build_config("en-US"))

    assert "--no-sandbox" in fake_options.arguments
    assert "--disable-dev-shm-usage" in fake_options.arguments
    assert "--hide-crash-restore-bubble" in fake_options.arguments


def test_build_chrome_locale_env_from_zh_cn() -> None:
    env = chrome._build_chrome_locale_env("zh-CN")

    assert env == {
        "LANG": "zh_CN.UTF-8",
        "LC_ALL": "zh_CN.UTF-8",
        "LANGUAGE": "zh_CN:zh",
    }


def test_chromium_browser_restores_locale_env_vars_after_startup(monkeypatch) -> None:
    fake_options = _FakeChromiumOptions()
    monkeypatch.setattr(chrome, "ChromiumOptions", lambda: fake_options)
    monkeypatch.setattr(chrome, "ChromiumPage", _FakeChromiumPage)
    monkeypatch.setattr(chrome, "cleanup_stale_chromium_singleton", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(chrome.ChromiumBrowser, "_ChromiumBrowser__instance", None)
    monkeypatch.setenv("LANG", "C.UTF-8")
    monkeypatch.setenv("LC_ALL", "C.UTF-8")
    monkeypatch.setenv("LANGUAGE", "C")

    chrome.ChromiumBrowser(headless=True, config=_build_config("zh-CN"))

    assert chrome.os.environ.get("LANG") == "C.UTF-8"
    assert chrome.os.environ.get("LC_ALL") == "C.UTF-8"
    assert chrome.os.environ.get("LANGUAGE") == "C"
