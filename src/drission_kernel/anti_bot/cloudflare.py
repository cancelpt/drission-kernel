"""Cloudflare bypass primitives for the extracted kernel."""

from __future__ import annotations

import logging
import time
from random import uniform
from typing import Any, Optional

from DrissionPage._elements.chromium_element import ShadowRoot
from DrissionPage._elements.none_element import NoneElement

logger = logging.getLogger(__name__)

title_keywords = ["Just a moment...", "请稍候…"]
verify_text = [
    "Verifying you are human. This may take a few seconds.",
    "正在验证您是否是真人。这可能需要几秒钟时间。",
    "正在进行安全验证",
]
operation_keywords = [
    "Verify you are human by completing the action below.",
    "请完成以下操作，验证您是真人。",
    "请验证您是真人执行安全验证",
    "请验证您是真人",
]
loading_keywords = ["Verifying...", "正在验证…"]
click_keywords = ["Verify you are human", "确认您是真人", "请验证您是真人"]


def _unwrap_page(page: Any) -> Any:
    return getattr(page, "raw", page)


def random_click(page: Any, x: int, y: int) -> None:
    """Perform a randomized click around coordinates (x, y)."""
    page = _unwrap_page(page)
    page.actions._dr.run(
        "Input.dispatchMouseEvent",
        type="mousePressed",
        button="left",
        clickCount=1,
        x=x + uniform(-5, 5),
        y=y + uniform(-5, 5),
        modifiers=page.actions.modifier,
    )

    time.sleep(uniform(0.1, 0.3))
    page.actions._dr.run(
        "Input.dispatchMouseEvent",
        type="mouseReleased",
        button="left",
        clickCount=1,
        x=x + uniform(-5, 5),
        y=y + uniform(-5, 5),
        modifiers=page.actions.modifier,
    )

    time.sleep(uniform(0.1, 0.3))


def bypass_cloudflare_component(page: Any, cf_component_sr: Optional[ShadowRoot] = None, offset_y: int = 0) -> bool:
    """Attempt to bypass Cloudflare component verification in a shadow root."""
    page = _unwrap_page(page)
    timeout = 20
    while True:
        cf_component = cf_component_sr.child().ele("tag=body", timeout=0.1).sr.children()[1].child().child()
        shadow_dom_1_parent = cf_component_sr.parent()
        if not isinstance(cf_component, NoneElement):
            if cf_component.text == "":
                logger.info("Cloudflare组件验证中")
                continue
            if cf_component.text in click_keywords:
                check_button = cf_component.ele("tag=input", timeout=0.1)
                target_x = shadow_dom_1_parent.rect.location[0] + check_button.rect.viewport_click_point[0]
                target_y = (
                    shadow_dom_1_parent.rect.location[1] + check_button.rect.viewport_click_point[1] + 10 - offset_y
                )

                page.actions._dr.run(
                    "Input.dispatchMouseEvent",
                    type="mouseMoved",
                    button="left",
                    clickCount=1,
                    x=target_x,
                    y=target_y,
                    modifiers=page.actions.modifier,
                )
                time.sleep(0.1)
                page.actions._dr.run(
                    "Input.dispatchMouseEvent",
                    type="mousePressed",
                    button="left",
                    clickCount=1,
                    x=target_x,
                    y=target_y,
                    modifiers=page.actions.modifier,
                )
                time.sleep(0.1)
                page.actions._dr.run(
                    "Input.dispatchMouseEvent",
                    type="mouseReleased",
                    button="left",
                    x=target_x + int(uniform(1, 10)),
                    y=target_y + int(uniform(1, 10)),
                    modifiers=page.actions.modifier,
                )
                time.sleep(2)
                break
            if "成功" in cf_component.text:
                return True
            if "失败" in cf_component.text:
                return False

        time.sleep(uniform(0.1, 0.3))
        timeout -= 0.1
        if timeout < 0:
            return False

    return True


def bypass_cloudflare(page: Any) -> bool:
    """Bypass full Cloudflare waiting room/check page."""
    page = _unwrap_page(page)
    title = page.title
    if not any(keyword in title for keyword in title_keywords):
        return True

    timeout_limit = 15
    end_time = time.perf_counter() + timeout_limit
    while time.perf_counter() < end_time:
        if not any(keyword in page.title for keyword in title_keywords):
            break

        h2 = page.ele(".:spacer-bottom")
        if isinstance(h2, NoneElement):
            time.sleep(1)
            continue

        h2_text = h2.text
        found_button = False
        try:
            if any(keyword in h2_text for keyword in verify_text):
                try:
                    shadow_dom_1_parent = page.ele(".:spacer-bottom").after().after().child().child()
                    shadow_dom_1 = shadow_dom_1_parent.sr
                    if isinstance(shadow_dom_1, NoneElement):
                        break

                    shadow_dom_2 = shadow_dom_1.child().active_ele.sr
                    if isinstance(shadow_dom_2, NoneElement):
                        break
                    shadow_dom_2.ele("tag:input")
                    found_button = True
                except Exception:
                    pass
                time.sleep(1)
                if not found_button:
                    continue
        except Exception:
            time.sleep(1)
            continue

        h2 = page.ele(".:spacer-bottom")
        if isinstance(h2, NoneElement) and not found_button:
            time.sleep(1)
            continue

        if found_button:
            try:
                shadow_dom_1_parent = page.ele(".:spacer-bottom").after().after().child().child()
                shadow_dom_1 = shadow_dom_1_parent.sr
                if isinstance(shadow_dom_1, NoneElement):
                    break

                shadow_dom_2 = shadow_dom_1.child().active_ele.sr
                if isinstance(shadow_dom_2, NoneElement):
                    break
                check_button = shadow_dom_2.ele("tag:input")

                page.actions._dr.run(
                    "Input.dispatchMouseEvent",
                    type="mouseMoved",
                    x=shadow_dom_1_parent.rect.location[0],
                    y=shadow_dom_1_parent.rect.location[1],
                    modifiers=page.actions.modifier,
                )
                time.sleep(1)

                page.actions._dr.run(
                    "Input.dispatchMouseEvent",
                    type="mousePressed",
                    button="left",
                    clickCount=1,
                    x=shadow_dom_1_parent.rect.location[0] + check_button.rect.location[0],
                    y=shadow_dom_1_parent.rect.location[1] + check_button.rect.location[1],
                    modifiers=page.actions.modifier,
                )
                time.sleep(0.1)
                page.actions._dr.run(
                    "Input.dispatchMouseEvent",
                    type="mouseReleased",
                    button="left",
                    x=shadow_dom_1_parent.rect.location[0] + check_button.rect.location[0] + int(uniform(1, 10)),
                    y=shadow_dom_1_parent.rect.location[1] + check_button.rect.location[1] + int(uniform(1, 10)),
                    modifiers=page.actions.modifier,
                )
                break
            except Exception:
                continue

    end_time = time.perf_counter() + timeout_limit
    while any(keyword in page.title for keyword in title_keywords):
        time.sleep(1)
        if time.perf_counter() >= end_time:
            return False
    return True
