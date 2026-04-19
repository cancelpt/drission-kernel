"""Browser-session adapters and Chromium bootstrap for the extracted kernel."""

from __future__ import annotations

import logging
import os
import socket
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from DrissionPage import ChromiumOptions
from DrissionPage._pages.chromium_page import ChromiumPage

from .tabs import DrissionTabHandle, ensure_tab_handle

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BrowserBootstrapConfig:
    """Caller-supplied browser bootstrap configuration for Chromium startup."""

    user_agent: str = "Mozilla/5.0"
    proxy: str | None = None
    download_path: Path | str = Path("/tmp/drission-kernel/download")
    user_data_dir: Path | str = Path("/tmp/drission-kernel/chrome-data")
    browser_path: Path | str | None = None
    language: str = "zh-CN"


def _parse_singleton_owner(lock_path: Path) -> tuple[str | None, int | None]:
    """Parse Chromium SingletonLock owner metadata."""
    raw_owner = ""
    try:
        if lock_path.is_symlink():
            raw_owner = os.readlink(lock_path)
        elif lock_path.exists():
            raw_owner = lock_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None, None

    if not raw_owner:
        return None, None

    host, sep, pid_part = raw_owner.rpartition("-")
    if not sep or not host:
        return None, None

    try:
        owner_pid = int(pid_part)
    except ValueError:
        return None, None

    return host, owner_pid


def _is_pid_alive(pid: int) -> bool:
    """Return whether a process is currently alive in this namespace."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _build_accept_languages(browser_language: str) -> str:
    """Build Chrome accept-languages preference from a locale token."""
    normalized = browser_language.strip()
    if not normalized:
        return ""
    if "," in normalized:
        return normalized

    primary_language = normalized.split("-")[0]
    if primary_language and primary_language != normalized:
        return f"{normalized},{primary_language}"
    return normalized


def _build_chrome_locale_env(browser_language: str) -> dict[str, str]:
    """Build locale-related env vars for Chromium process startup."""
    normalized = browser_language.strip()
    if not normalized:
        return {}

    locale_token = normalized.split(",")[0].strip()
    if not locale_token:
        return {}

    locale_name = locale_token.replace("-", "_")
    locale_utf8 = locale_name if "." in locale_name else f"{locale_name}.UTF-8"
    primary_language = locale_name.split("_")[0]
    language_chain = f"{locale_name}:{primary_language}" if primary_language else locale_name
    return {
        "LANG": locale_utf8,
        "LC_ALL": locale_utf8,
        "LANGUAGE": language_chain,
    }


def cleanup_stale_chromium_singleton(
    profile_dir: Path,
    *,
    current_host: str | None = None,
    pid_alive_checker: Any = None,
) -> bool:
    """
    Remove stale Chromium singleton lock artifacts from a profile directory.

    Returns True when cleanup removed any lock artifact.
    """
    current_host = current_host or socket.gethostname()
    pid_alive_checker = pid_alive_checker or _is_pid_alive

    lock_path = profile_dir / "SingletonLock"
    if not (lock_path.exists() or lock_path.is_symlink()):
        return False

    owner_host, owner_pid = _parse_singleton_owner(lock_path)
    remove_locks = False

    if owner_host is None and owner_pid is None:
        remove_locks = True
    elif owner_host != current_host:
        remove_locks = True
    elif owner_pid is not None and not pid_alive_checker(owner_pid):
        remove_locks = True

    if not remove_locks:
        return False

    removed_any = False
    for file_name in ("SingletonCookie", "SingletonLock", "SingletonSocket"):
        target = profile_dir / file_name
        try:
            target.unlink()
            removed_any = True
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning("Failed to remove stale Chromium lock file %s: %s", target, exc)

    return removed_any


class ChromiumBrowser:
    """Chromium browser singleton that manages named raw browser tabs."""

    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(
        self,
        headless: bool = False,
        max_tabs: int = 10,
        config: BrowserBootstrapConfig | None = None,
    ):
        self._page: ChromiumPage
        self.max_tabs = max_tabs
        self.lock = threading.RLock()
        self._tab_slots = threading.Condition(self.lock)
        self.stop_flag = False
        self.tabs: dict[str, Any] = {}
        config = config or BrowserBootstrapConfig()
        download_path = Path(config.download_path)
        user_data_dir = Path(config.user_data_dir)

        co = ChromiumOptions().headless(headless)
        co.set_argument("--window-size=1920,1000")

        browser_language = str(config.language or "zh-CN").strip()
        locale_env: dict[str, str] = {}
        if browser_language:
            locale_env = _build_chrome_locale_env(browser_language)
            co.set_argument(f"--lang={browser_language}")
            accepted_languages = _build_accept_languages(browser_language)
            co.set_pref("intl.accept_languages", accepted_languages)
            co.set_pref("intl.selected_languages", accepted_languages)

        co.set_user_agent(config.user_agent)

        if config.proxy:
            co.set_proxy(config.proxy)

        co.set_pref("download.prompt_for_download", False)
        co.set_pref("download.directory_upgrade", True)
        co.set_pref("safebrowsing.enabled", False)
        co.set_pref("safebrowsing.disable_download_protection", True)
        co.set_download_path(download_path)
        co.set_user_data_path(user_data_dir)
        profile_dir = user_data_dir
        if cleanup_stale_chromium_singleton(profile_dir):
            logger.info("Removed stale Chromium Singleton* locks from %s", profile_dir)
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-dev-shm-usage")
        if config.browser_path is not None:
            co.set_browser_path(Path(config.browser_path))
        co.set_pref("credentials_enable_service", False)
        co.set_argument("--hide-crash-restore-bubble")

        previous_locale_env: dict[str, str | None] = {}
        for env_key, env_value in locale_env.items():
            previous_locale_env[env_key] = os.environ.get(env_key)
            os.environ[env_key] = env_value
        try:
            self.page = ChromiumPage(co)
        finally:
            for env_key, previous_value in previous_locale_env.items():
                if previous_value is None:
                    os.environ.pop(env_key, None)
                else:
                    os.environ[env_key] = previous_value

    def get_tab(self, site_name: str):
        """Get or create the raw tab object for a named site context."""
        with self._tab_slots:
            while True:
                if site_name in self.tabs:
                    return self.tabs[site_name]
                if self.stop_flag:
                    return None
                if len(self.tabs) < self.max_tabs:
                    logger.debug("new tab")
                    self.tabs[site_name] = self.page.new_tab()
                    return self.tabs[site_name]
                self._tab_slots.wait()

    def open_url(self, site_name: str, url: str, timeout: int = 10):
        """Open a URL in the named tab and return the raw tab object."""
        tab = self.get_tab(site_name)
        if tab is None:
            return None
        tab.get(url, timeout=timeout)
        return tab

    def set_cookies(self, cookies: list | dict | str) -> None:
        """Set cookies for the browser."""
        self.page.set.cookies(cookies)

    def get_cookies(self, target_domain: str | None = None) -> list | dict:
        """Get browser cookies, optionally filtered by domain."""
        all_cookies = self.page.cookies(as_dict=False, all_domains=True)
        if target_domain:
            return [cookie for cookie in all_cookies if target_domain in cookie["domain"]]
        return all_cookies

    def set_local_storage(self, site_name: str, local_storage: dict) -> None:
        """Set local storage items for a site."""
        tab = self.get_tab(site_name)
        if tab is None:
            return
        for key, value in local_storage.items():
            tab.set.local_storage(key, value)

    def get_local_storage(self, site_name: str) -> dict:
        """Get local storage items from a site."""
        tab = self.get_tab(site_name)
        if tab is None:
            return {}
        return tab.local_storage()

    def listen_start(self, site_name: str, url: str) -> None:
        """Start listening for network requests matching the URL."""
        tab = self.get_tab(site_name)
        if tab is not None:
            tab.listen.start(url)

    def listen_wait(self, site_name: str, count: int = 1, timeout: int = 10):
        """Wait for listened requests to be captured."""
        tab = self.get_tab(site_name)
        if tab is None:
            return None
        return tab.listen.wait(count=count, timeout=timeout)

    def listen_stop(self, site_name: str) -> None:
        """Stop listening for network requests."""
        tab = self.get_tab(site_name)
        if tab is not None:
            tab.listen.stop()

    def close(self, site_name: str) -> None:
        """Close a specific site's tab and free its slot."""
        with self._tab_slots:
            tab = self.tabs.pop(site_name, None)
            self._tab_slots.notify_all()
        if tab is None:
            return
        close = getattr(tab, "close", None)
        if callable(close):
            close()

    def quit(self) -> None:
        """Quit the browser instance and close all windows."""
        with self._tab_slots:
            self.stop_flag = True
            self.tabs.clear()
            self._tab_slots.notify_all()
        self.page.quit()


class DrissionBrowserSession:
    """Session adapter that exposes named tab handles over a Chromium-like browser."""

    def __init__(self, browser: Any) -> None:
        if browser is None:
            raise ValueError("browser is required")
        self._browser = browser
        self._lock = threading.RLock()
        self._tabs: dict[str, DrissionTabHandle] = {}
        self._closed = False

    @property
    def raw(self) -> Any:
        """Expose the wrapped browser object."""
        return self._browser

    @property
    def closed(self) -> bool:
        """Return whether the session has already been shut down."""
        return self._closed

    def set_cookies(self, cookies: Any) -> None:
        """Load cookies into the underlying browser session."""
        self._browser.set_cookies(cookies)

    def get_tab(self, site_name: str) -> DrissionTabHandle:
        """Return a stable tab handle for the requested site name."""
        with self._lock:
            if self._closed:
                raise RuntimeError("browser session is closed")
            handle = self._tabs.get(site_name)
            if handle is not None:
                return handle

            raw_tab = self._browser.get_tab(site_name)
            if raw_tab is None:
                raise RuntimeError("browser session is stopped")
            handle = ensure_tab_handle(raw_tab, session=self, name=site_name)
            self._tabs[site_name] = handle
            return handle

    def close_tab(self, site_name: str) -> None:
        """Close one named tab and invalidate any issued handle."""
        with self._lock:
            handle = self._tabs.pop(site_name, None)
        if hasattr(self._browser, "close"):
            self._browser.close(site_name)
        elif handle is not None and hasattr(handle.raw, "close"):
            handle.raw.close()
        if handle is not None:
            handle.invalidate()

    def quit(self) -> None:
        """Shut down the session and invalidate all issued tab handles."""
        with self._lock:
            handles = list(self._tabs.values())
            self._tabs.clear()
            self._closed = True
        for handle in handles:
            handle.invalidate()
        quit_browser = getattr(self._browser, "quit", None)
        if callable(quit_browser):
            quit_browser()

    def get_cookies(self, target_domain: str | None = None) -> list[dict[str, Any]]:
        """Return browser cookies, optionally filtered by target domain."""
        return self._browser.get_cookies(target_domain=target_domain)

    def get_local_storage(self, site_name: str) -> dict[str, Any]:
        """Return local storage for the requested site tab."""
        return self._browser.get_local_storage(site_name)

    def set_local_storage(self, site_name: str, payload: dict[str, Any]) -> None:
        """Write local storage payload for the requested site tab."""
        self._browser.set_local_storage(site_name, payload)


def create_browser_session(
    browser: Any = None,
    headless: bool = False,
    config: BrowserBootstrapConfig | None = None,
) -> DrissionBrowserSession:
    """Create a DrissionPage browser session adapter."""
    if isinstance(browser, DrissionBrowserSession):
        return browser
    if browser is None:
        browser = ChromiumBrowser(headless=headless, config=config)
    return DrissionBrowserSession(browser=browser)
