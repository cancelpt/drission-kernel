"""Tests for the repository-owned Docker browser smoke helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_smoke_module() -> ModuleType:
    root_dir = Path(__file__).resolve().parents[3]
    module_path = root_dir / "tools" / "smoke" / "headless_browser_smoke.py"
    spec = importlib.util.spec_from_file_location("headless_browser_smoke", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_browser_path_prefers_environment_override(monkeypatch, tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    browser_path = tmp_path / "chromium"
    browser_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("DRISSION_KERNEL_BROWSER_PATH", str(browser_path))
    monkeypatch.setattr(smoke.shutil, "which", lambda _name: None)

    assert smoke.resolve_browser_path() == browser_path


def test_run_browser_smoke_serves_local_page_and_quits_session(monkeypatch, tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    observed: dict[str, object] = {}

    class _FakeTab:
        title = "drission-kernel smoke"

        def get(self, url: str, timeout: int = 10, retry: int = 0):
            observed["url"] = url
            observed["timeout"] = timeout
            observed["retry"] = retry
            return {"url": url}

    class _FakeSession:
        def __init__(self) -> None:
            self.tab = _FakeTab()

        def get_tab(self, name: str) -> _FakeTab:
            observed["tab_name"] = name
            return self.tab

        def quit(self) -> None:
            observed["quit_called"] = True

    def _fake_create_browser_session(*, headless: bool, config):
        observed["headless"] = headless
        observed["config"] = config
        return _FakeSession()

    def _fake_wait_for_title(tab, expected_title: str, timeout: float = 10) -> None:
        observed["wait_title"] = (tab.title, expected_title, timeout)

    def _fake_wait_for_element(tab, selector: str, timeout: float = 10, index: int = 1):
        observed["wait_element"] = (selector, timeout, index)
        return SimpleNamespace(text="browser smoke")

    monkeypatch.setattr(smoke, "create_browser_session", _fake_create_browser_session)
    monkeypatch.setattr(smoke, "wait_for_title", _fake_wait_for_title)
    monkeypatch.setattr(smoke, "wait_for_element", _fake_wait_for_element)

    smoke.run_browser_smoke(
        browser_path=tmp_path / "chromium",
        workspace=tmp_path,
    )

    assert observed["headless"] is True
    assert observed["tab_name"] == "docker-smoke"
    assert str(observed["url"]).startswith("http://127.0.0.1:")
    assert observed["wait_title"] == ("drission-kernel smoke", "drission-kernel smoke", 10)
    assert observed["wait_element"] == ("tag:h1", 10, 1)
    assert observed["quit_called"] is True
