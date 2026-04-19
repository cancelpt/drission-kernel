"""SafeLine bypass primitives for the extracted kernel."""

from __future__ import annotations

import logging
import time
from random import uniform
from typing import Any

from DrissionPage._elements.none_element import NoneElement

logger = logging.getLogger(__name__)


def _unwrap_page(page: Any) -> Any:
    return getattr(page, "raw", page)


def bypass_ctlc(page: Any) -> bool:
    """Bypass ChangTing LeiChi (SafeLine) protection flows."""
    page = _unwrap_page(page)
    sl = page.ele('x://*[@id="sl-slider"]', timeout=20)

    if sl is not None and not isinstance(sl, NoneElement):
        page.actions.hold(sl)
        page.actions._dr.run(
            "Input.dispatchMouseEvent",
            type="mousePressed",
            button="left",
            clickCount=1,
            x=sl.rect.location[0] + 23,
            y=sl.rect.location[1] + 32,
            modifiers=page.actions.modifier,
        )

        total_distance = 510
        initial_speed = 10
        max_speed = 1000
        acceleration = 30
        deceleration = 30

        temp_x = sl.rect.location[0]
        temp_y = sl.rect.location[1]

        current_position = sl.rect.location[0]
        target_position = current_position + total_distance
        current_speed = initial_speed

        while current_position < target_position:
            if current_speed < max_speed:
                current_speed += acceleration
            elif current_position + current_speed > target_position:
                current_speed -= deceleration
                if current_speed < 0:
                    current_speed = 0

            current_position += current_speed * 0.1

            y_offset = int(100 * (1 - ((current_position - sl.rect.location[0]) / total_distance) ** 2))
            y = int(sl.rect.location[1] + y_offset)

            if current_position >= target_position:
                current_position = target_position

            x = int(current_position) + int(uniform(-5, 5))

            page.actions._dr.run(
                "Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, modifiers=page.actions.modifier
            )

            time.sleep(0.01)

        page.actions._dr.run(
            "Input.dispatchMouseEvent",
            type="mouseReleased",
            button="left",
            x=temp_x + total_distance,
            y=temp_y + 32,
            modifiers=page.actions.modifier,
        )

        time.sleep(1)
        page.actions.release()

    timeout = 15
    while True:
        if (
            not isinstance(page.ele("验证完成", timeout=1), NoneElement)
            or not isinstance(page.ele("Verification Complete", timeout=1), NoneElement)
            or isinstance(page.ele("@id=sl-box", timeout=1), NoneElement)
        ):
            return True
        time.sleep(1)
        timeout -= 1
        logger.info("等待验证完成: %ss", timeout)

        if timeout <= 0:
            logger.error("验证失败，最后等待结果超时")
            return False
