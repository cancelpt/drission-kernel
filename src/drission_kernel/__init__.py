"""Internal reusable DrissionPage automation kernel."""

from __future__ import annotations

from . import anti_bot
from .helpers import url_contains, wait_for_element, wait_for_title
from .protocols import BrowserSession, ListenerHandle, TabHandle
from .session import (
    BrowserBootstrapConfig,
    ChromiumBrowser,
    DrissionBrowserSession,
    _build_accept_languages,
    _build_chrome_locale_env,
    _parse_singleton_owner,
    cleanup_stale_chromium_singleton,
    create_browser_session,
)
from .tabs import DrissionTabHandle, InvalidTabHandleError, ensure_tab_handle

__all__ = [
    "BrowserSession",
    "BrowserBootstrapConfig",
    "ChromiumBrowser",
    "DrissionBrowserSession",
    "DrissionTabHandle",
    "InvalidTabHandleError",
    "ListenerHandle",
    "TabHandle",
    "_build_accept_languages",
    "_build_chrome_locale_env",
    "_parse_singleton_owner",
    "anti_bot",
    "cleanup_stale_chromium_singleton",
    "create_browser_session",
    "ensure_tab_handle",
    "url_contains",
    "wait_for_element",
    "wait_for_title",
]
