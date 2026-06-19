"""Unit tests for the extracted drission_kernel anti-bot helpers."""

from __future__ import annotations

import drission_kernel.anti_bot.cloudflare as cloudflare
from drission_kernel import anti_bot


class _MissingElement:
    pass


class _FakePage:
    def __init__(
        self, *, title: str = "", html: str = "", slider_present: bool = False, client_verifying: bool = False
    ) -> None:
        self.title = title
        self.html = html
        self.slider_present = slider_present
        self.client_verifying = client_verifying

    def ele(self, selector: str, timeout: float = 0.2):
        _ = timeout
        if selector == "x://*[@id='sl-slider']":
            return object() if self.slider_present else _MissingElement()
        if selector == "正在进行安全检测":
            return object() if self.client_verifying else _MissingElement()
        if selector == "Client Verifying":
            return object() if self.client_verifying else _MissingElement()
        return _MissingElement()


def test_auto_bypass_dispatches_safeline_when_slider_marker_present(monkeypatch) -> None:
    page = _FakePage(slider_present=True)
    monkeypatch.setattr(anti_bot, "NoneElement", _MissingElement)
    monkeypatch.setattr(anti_bot, "bypass_ctlc", lambda received: received is page)

    assert anti_bot.auto_bypass(page) is True


def test_auto_bypass_dispatches_cloudflare_on_waiting_room_title(monkeypatch) -> None:
    page = _FakePage(title="Just a moment...")
    monkeypatch.setattr(anti_bot, "NoneElement", _MissingElement)
    monkeypatch.setattr(anti_bot, "bypass_cloudflare", lambda received: received is page)

    assert anti_bot.auto_bypass(page) is True


def test_auto_bypass_returns_success_when_page_has_no_supported_challenge(monkeypatch) -> None:
    monkeypatch.setattr(anti_bot, "NoneElement", _MissingElement)

    assert anti_bot.auto_bypass(_FakePage(title="Welcome", html="<html>ok</html>")) is True


class _FakeRect:
    def __init__(self, *, location=(0, 0), viewport_click_point=(0, 0)) -> None:
        self.location = location
        self.viewport_click_point = viewport_click_point


class _FakeDriver:
    def __init__(self, page) -> None:
        self.page = page
        self.calls: list[dict[str, object]] = []

    def run(self, _method: str, **kwargs) -> None:
        self.calls.append(kwargs)
        if kwargs.get("type") == "mouseReleased":
            self.page.challenge_solved = True


class _FakeActions:
    def __init__(self, page) -> None:
        self._dr = _FakeDriver(page)
        self.modifier = 0


class _FakeInput:
    def __init__(self, *, location=(0, 0), viewport_click_point=(12, 8)) -> None:
        self.rect = _FakeRect(location=location, viewport_click_point=viewport_click_point)


class _FakeFrameActiveElement:
    def __init__(self, shadow_root) -> None:
        self.sr = shadow_root


class _FakeFrame:
    _type = "ChromiumFrame"
    tag = "iframe"

    def __init__(self, *, location=(240, 320), shadow_root) -> None:
        self.frame_ele = type("FrameElement", (), {"rect": _FakeRect(location=location)})()
        self.active_ele = _FakeFrameActiveElement(shadow_root)


class _FakeShadowRoot:
    def __init__(
        self,
        *,
        parent=None,
        input_element=None,
        iframe=None,
        children=None,
    ) -> None:
        self._parent = parent
        self._input = input_element
        self._iframe = iframe
        self._children = list(children or [])

    def parent(self):
        return self._parent

    def ele(self, locator: str, timeout: float = 0.1):
        _ = timeout
        if locator in {"tag:input", "tag=input"}:
            return self._input if self._input is not None else _MissingElement()
        if locator in {"tag:iframe", "tag=iframe", "tag:frame", "tag=frame"}:
            return self._iframe if self._iframe is not None else _MissingElement()
        if locator == "tag=body":
            return _MissingElement()
        return _MissingElement()

    def eles(self, locator: str, timeout: float = 0.1):
        _ = timeout
        if locator in {"tag:iframe", "tag=iframe", "tag:frame", "tag=frame"}:
            return [self._iframe] if self._iframe is not None else []
        if locator == "xpath:.//*[name()='iframe' or name()='frame']":
            return [self._iframe] if self._iframe is not None else []
        if locator == "xpath:.//*":
            return list(self._children)
        return []

    def children(self):
        return list(self._children)


class _FakeHostElement:
    def __init__(self, *, shadow_root=None, location=(100, 200)) -> None:
        self.rect = _FakeRect(location=location)
        self.sr = shadow_root if shadow_root is not None else _MissingElement()


class _FakeChallengePage:
    def __init__(self, host) -> None:
        self.html = "<html><body><div id='challenge-platform'></div></body></html>"
        self._host = host
        self.actions = _FakeActions(self)
        self.challenge_solved = False

    @property
    def title(self) -> str:
        return "Welcome" if self.challenge_solved else "Just a moment..."

    def ele(self, selector: str, timeout: float = 0.1):
        _ = timeout
        if selector == ".:spacer-bottom":
            return _MissingElement()
        raise AssertionError(selector)

    def eles(self, selector: str, timeout: float = 0.1):
        _ = timeout
        if selector == "xpath://*":
            return [self._host]
        return []


def _make_shadow_iframe_challenge_page() -> tuple[_FakeChallengePage, _FakeShadowRoot]:
    checkbox = _FakeInput()
    frame_shadow_root = _FakeShadowRoot(input_element=checkbox)
    frame = _FakeFrame(shadow_root=frame_shadow_root)
    challenge_shadow_root = _FakeShadowRoot(iframe=frame)
    host = _FakeHostElement(shadow_root=challenge_shadow_root)
    challenge_shadow_root._parent = host
    return _FakeChallengePage(host), challenge_shadow_root


def test_bypass_cloudflare_finds_turnstile_inside_shadow_root_iframe(monkeypatch) -> None:
    page, _challenge_shadow_root = _make_shadow_iframe_challenge_page()
    tick = {"value": 0}

    def _perf_counter() -> float:
        tick["value"] += 1
        return tick["value"]

    monkeypatch.setattr(cloudflare, "NoneElement", _MissingElement)
    monkeypatch.setattr(cloudflare.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cloudflare.time, "perf_counter", _perf_counter)

    assert cloudflare.bypass_cloudflare(page) is True
    assert any(call.get("type") == "mousePressed" for call in page.actions._dr.calls)


def test_bypass_cloudflare_component_finds_turnstile_inside_shadow_root_iframe(monkeypatch) -> None:
    page, challenge_shadow_root = _make_shadow_iframe_challenge_page()

    monkeypatch.setattr(cloudflare, "NoneElement", _MissingElement)
    monkeypatch.setattr(cloudflare.time, "sleep", lambda *_args, **_kwargs: None)

    assert cloudflare.bypass_cloudflare_component(page, challenge_shadow_root) is True
    assert any(call.get("type") == "mousePressed" for call in page.actions._dr.calls)
