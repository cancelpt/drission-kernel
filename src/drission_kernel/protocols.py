"""Protocol contracts for the extracted DrissionPage kernel."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ListenerHandle(Protocol):
    """Bounded listener operations exposed through a tab handle."""

    def start(self, *args, **kwargs) -> None:
        """Start listening for matching network traffic."""

    def wait(self, *args, **kwargs) -> Any:
        """Wait for one or more matching packets."""

    def stop(self) -> None:
        """Stop the active listener when present."""


@runtime_checkable
class TabHandle(Protocol):
    """Stable tab wrapper for shared browser operations."""

    name: str

    @property
    def raw(self) -> Any:
        """Expose the wrapped raw DrissionPage tab for transitional callers."""

    @property
    def listen(self) -> ListenerHandle:
        """Expose bounded listener operations."""

    @property
    def url(self) -> str:
        """Return the current page URL."""

    @property
    def title(self) -> str:
        """Return the current page title."""

    @property
    def html(self) -> str:
        """Return the current page HTML."""

    def get(self, url: str, timeout: int = 10, retry: int = 0):
        """Navigate the wrapped tab to a new URL."""

    def ele(self, selector: str, timeout: float = 0, index: int = 1) -> Any:
        """Find one element in the current page."""

    def eles(self, selector: str, timeout: float = 0) -> Any:
        """Find multiple elements in the current page."""

    def refresh(self) -> None:
        """Refresh the current page."""

    def run_js(self, script: str) -> Any:
        """Run JavaScript in the current page context."""


@runtime_checkable
class BrowserSession(Protocol):
    """Browser-session contract shared across reusable automation flows."""

    @property
    def raw(self) -> Any:
        """Expose the wrapped browser implementation."""

    def set_cookies(self, cookies: Any) -> None:
        """Load cookies into the browser context."""

    def get_tab(self, site_name: str) -> TabHandle:
        """Return the named reusable tab handle."""

    def close_tab(self, site_name: str) -> None:
        """Close one named tab and invalidate its issued handle."""

    def quit(self) -> None:
        """Shut down the full browser session."""

    def get_cookies(self, target_domain: str | None = None) -> list[dict[str, Any]]:
        """Return cookies, optionally filtered by domain."""

    def get_local_storage(self, site_name: str) -> dict[str, Any]:
        """Read local storage payload for a named tab context."""

    def set_local_storage(self, site_name: str, payload: dict[str, Any]) -> None:
        """Write local storage payload for a named tab context."""
