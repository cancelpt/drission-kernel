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
INPUT_LOCATORS = ("tag:input", "tag=input")
FRAME_LOCATORS = ("tag:iframe", "tag=iframe", "tag:frame", "tag=frame", "xpath:.//*[name()='iframe' or name()='frame']")


def _is_missing(element: Any) -> bool:
    return element is None or isinstance(element, NoneElement)


def _safe_children(container: Any) -> list[Any]:
    try:
        children = container.children()
    except Exception:
        return []
    return [child for child in children or [] if not _is_missing(child)]


def _safe_eles(container: Any, locator: str) -> list[Any]:
    try:
        elements = container.eles(locator, timeout=0.1)
    except TypeError:
        try:
            elements = container.eles(locator)
        except Exception:
            return []
    except Exception:
        return []
    return [element for element in elements or [] if not _is_missing(element)]


def _safe_ele(container: Any, locator: str) -> Any:
    try:
        element = container.ele(locator, timeout=0.1)
    except Exception:
        return None
    return None if _is_missing(element) else element


def _shadow_root_of(element: Any) -> Any:
    try:
        shadow_root = element.sr
    except Exception:
        return None
    return None if _is_missing(shadow_root) else shadow_root


def _iter_descendants(container: Any) -> list[Any]:
    seen: set[int] = set()
    descendants: list[Any] = []
    for locator in ("xpath:.//*", "xpath://*"):
        for element in _safe_eles(container, locator):
            marker = id(element)
            if marker in seen:
                continue
            seen.add(marker)
            descendants.append(element)

    for element in _safe_children(container):
        marker = id(element)
        if marker in seen:
            continue
        seen.add(marker)
        descendants.append(element)
    return descendants


def _frame_anchor(frame: Any) -> Any:
    return getattr(frame, "frame_ele", None) or frame


def _resolve_click_coordinates(target: Any, anchor: Any = None, offset_y: int = 0) -> Optional[tuple[int, int]]:
    target_rect = getattr(target, "rect", None)
    if target_rect is None:
        return None

    if anchor is not None:
        anchor_location = getattr(getattr(anchor, "rect", None), "location", None)
        viewport_click_point = getattr(target_rect, "viewport_click_point", None)
        if anchor_location and viewport_click_point:
            return (
                int(anchor_location[0] + viewport_click_point[0]),
                int(anchor_location[1] + viewport_click_point[1] - offset_y),
            )

        target_location = getattr(target_rect, "location", None)
        if anchor_location and target_location:
            return (
                int(anchor_location[0] + target_location[0]),
                int(anchor_location[1] + target_location[1] - offset_y),
            )

    viewport_click_point = getattr(target_rect, "viewport_click_point", None)
    if viewport_click_point:
        return int(viewport_click_point[0]), int(viewport_click_point[1])

    target_location = getattr(target_rect, "location", None)
    if target_location:
        return int(target_location[0]), int(target_location[1] - offset_y)

    return None


def _find_direct_input(container: Any) -> Any:
    for locator in INPUT_LOCATORS:
        input_element = _safe_ele(container, locator)
        if input_element is not None:
            return input_element
    return None


def _find_cloudflare_candidate_in_frame(frame: Any, visited: set[int]) -> Optional[tuple[Any, Any]]:
    active_element = getattr(frame, "active_ele", None)
    active_shadow_root = _shadow_root_of(active_element)
    if active_shadow_root is not None:
        candidate = _find_cloudflare_candidate_in_shadow_root(active_shadow_root, visited)
        if candidate is not None:
            _anchor, target = candidate
            return _frame_anchor(frame), target

    input_element = _find_direct_input(frame)
    if input_element is not None:
        return _frame_anchor(frame), input_element

    for element in _iter_descendants(frame):
        candidate = _find_cloudflare_candidate_in_element(element, visited)
        if candidate is not None:
            anchor, target = candidate
            return (anchor or _frame_anchor(frame)), target
    return None


def _find_cloudflare_candidate_in_shadow_root(shadow_root: Any, visited: set[int]) -> Optional[tuple[Any, Any]]:
    marker = id(shadow_root)
    if marker in visited:
        return None
    visited.add(marker)

    input_element = _find_direct_input(shadow_root)
    if input_element is not None:
        return None, input_element

    for frame in _safe_eles(shadow_root, "xpath:.//*[name()='iframe' or name()='frame']"):
        candidate = _find_cloudflare_candidate_in_frame(frame, visited)
        if candidate is not None:
            return candidate

    for locator in FRAME_LOCATORS:
        frame = _safe_ele(shadow_root, locator)
        if frame is None:
            continue
        candidate = _find_cloudflare_candidate_in_frame(frame, visited)
        if candidate is not None:
            return candidate

    for element in _iter_descendants(shadow_root):
        candidate = _find_cloudflare_candidate_in_element(element, visited)
        if candidate is not None:
            return candidate
    return None


def _find_cloudflare_candidate_in_element(element: Any, visited: set[int]) -> Optional[tuple[Any, Any]]:
    if getattr(element, "_type", None) == "ChromiumFrame" or getattr(element, "tag", None) in {"iframe", "frame"}:
        return _find_cloudflare_candidate_in_frame(element, visited)

    shadow_root = _shadow_root_of(element)
    if shadow_root is not None:
        return _find_cloudflare_candidate_in_shadow_root(shadow_root, visited)
    return None


def _find_cloudflare_candidate(page: Any, root: Any = None) -> Optional[tuple[Any, Any]]:
    visited: set[int] = set()
    if root is not None and not _is_missing(root):
        return _find_cloudflare_candidate_in_shadow_root(root, visited)

    for element in _iter_descendants(page):
        candidate = _find_cloudflare_candidate_in_element(element, visited)
        if candidate is not None:
            return candidate
    return None


def _click_cloudflare_candidate(page: Any, anchor: Any, target: Any, offset_y: int = 0) -> bool:
    click_coordinates = _resolve_click_coordinates(target, anchor=anchor, offset_y=offset_y)
    if click_coordinates is None:
        return False

    target_x, target_y = click_coordinates
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
    random_click(page, target_x, target_y)
    return True


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
        if cf_component_sr is None or _is_missing(cf_component_sr):
            raise AttributeError("Cloudflare component shadow root unavailable")

        candidate = _find_cloudflare_candidate(page, cf_component_sr)
        if candidate is not None:
            anchor, target = candidate
            if _click_cloudflare_candidate(page, anchor, target, offset_y=offset_y):
                time.sleep(2)
                return True

        time.sleep(uniform(0.1, 0.3))
        timeout -= 0.1
        if timeout < 0:
            return False


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

        candidate = _find_cloudflare_candidate(page)
        if candidate is None:
            time.sleep(1)
            continue

        anchor, target = candidate
        if _click_cloudflare_candidate(page, anchor, target):
            break

    end_time = time.perf_counter() + timeout_limit
    while any(keyword in page.title for keyword in title_keywords):
        time.sleep(1)
        if time.perf_counter() >= end_time:
            return False
    return True
