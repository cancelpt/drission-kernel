"""Reusable browser helper functions built on the kernel tab surface."""

from __future__ import annotations

import logging
import time

from DrissionPage._elements.none_element import NoneElement

logger = logging.getLogger(__name__)


def wait_for_title(tab, expected_title: str, timeout: float = 10) -> None:
    """Wait until the current page title contains the expected text."""
    start_time = time.time()
    while expected_title not in str(getattr(tab, "title", "") or ""):
        time.sleep(0.2)
        if time.time() - start_time > timeout:
            logger.error("获取 %s 标题等待超时", expected_title)
            raise Exception(f"获取 {expected_title} 标题等待超时")


def url_contains(tab, expected_url: str, timeout: float = 0.2) -> bool:
    """Return whether the current URL contains the expected text within the timeout."""
    start_time = time.time()
    while expected_url not in str(getattr(tab, "url", "") or ""):
        time.sleep(0.2)
        if time.time() - start_time > timeout:
            return False
    return True


def wait_for_element(tab, selector: str, timeout: float = 10, index: int = 1):
    """Wait for one element and raise when it never appears."""
    logger.info("%s 等待元素 '%s'", getattr(tab, "title", ""), selector)
    element = tab.ele(selector, timeout=timeout, index=index)
    logger.info("%s 等待元素 '%s' 结束", getattr(tab, "title", ""), selector)
    if isinstance(element, NoneElement):
        logger.error("%s 获取元素 '%s' 等待超时", getattr(tab, "title", ""), selector)
        raise Exception(f"获取元素 '{selector}' 等待超时")
    return element
