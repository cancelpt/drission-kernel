"""Unit tests for the extracted drission_kernel anti-bot helpers."""

from __future__ import annotations

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
