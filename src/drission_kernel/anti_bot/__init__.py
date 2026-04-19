"""Anti-bot helpers exported by the extracted DrissionPage kernel."""

from __future__ import annotations

from DrissionPage._elements.none_element import NoneElement

from .cloudflare import bypass_cloudflare, bypass_cloudflare_component, random_click
from .safeline import bypass_ctlc


def auto_bypass(page) -> bool:
    """Detect and bypass known anti-bot challenge pages."""
    if not isinstance(page.ele("x://*[@id='sl-slider']", timeout=0.2), NoneElement) or "雷池" in page.html:
        return bypass_ctlc(page)
    if "请稍候" in page.title or "Just a moment" in page.title:
        for _ in range(3):
            if bypass_cloudflare(page):
                return True
        return False
    if not isinstance(page.ele("正在进行安全检测", timeout=0.2), NoneElement) or not isinstance(
        page.ele("Client Verifying", timeout=0.2), NoneElement
    ):
        return bypass_ctlc(page)
    return True


__all__ = [
    "auto_bypass",
    "bypass_cloudflare",
    "bypass_cloudflare_component",
    "bypass_ctlc",
    "random_click",
]
