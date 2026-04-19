"""Tab-handle adapters for the extracted DrissionPage kernel."""

from __future__ import annotations

from typing import Any


class InvalidTabHandleError(RuntimeError):
    """Raised when a caller uses a tab handle after it has been invalidated."""


class DrissionListenerHandle:
    """Bounded listener wrapper that guarantees cleanup after wait operations."""

    def __init__(self, tab: "DrissionTabHandle") -> None:
        self._tab = tab
        self._active = False

    def _raw_listener(self):
        """Return the wrapped raw listener object when available."""
        return getattr(self._tab.raw, "listen", None)

    def start(self, *args, **kwargs) -> None:
        """Start the wrapped network listener and mark it active."""
        listener = self._raw_listener()
        if listener is None:
            raise AttributeError("Wrapped tab does not expose listen")
        listener.start(*args, **kwargs)
        self._active = True

    def wait(self, *args, **kwargs):
        """Wait for listener results and always stop the listener afterward."""
        listener = self._raw_listener()
        if listener is None:
            raise AttributeError("Wrapped tab does not expose listen")
        try:
            return listener.wait(*args, **kwargs)
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the wrapped listener if it is currently active."""
        if not self._active:
            return
        listener = self._raw_listener()
        self._active = False
        if listener is None:
            return
        stop = getattr(listener, "stop", None)
        if callable(stop):
            stop()

    def invalidate(self) -> None:
        """Invalidate the listener wrapper and swallow cleanup failures."""
        try:
            self.stop()
        except Exception:
            self._active = False

    def __getattr__(self, name: str) -> Any:
        listener = self._raw_listener()
        if listener is None:
            raise AttributeError(name)
        return getattr(listener, name)


class DrissionTabHandle:
    """Named tab wrapper that keeps lifecycle ownership in the session layer."""

    def __init__(self, raw_tab: Any, *, name: str, session: Any | None = None) -> None:
        self.name = name
        self._raw_tab = raw_tab
        self._session = session
        self._invalid = False
        self._listener = DrissionListenerHandle(self)

    def invalidate(self) -> None:
        """Mark this handle invalid and invalidate its bounded listener."""
        self._invalid = True
        self._listener.invalidate()

    def _ensure_valid(self) -> Any:
        if self._invalid:
            raise InvalidTabHandleError("Tab handle is no longer valid")
        session = self._session
        if session is not None and getattr(session, "closed", False):
            raise InvalidTabHandleError("Tab handle is no longer valid")
        return self._raw_tab

    @property
    def raw(self) -> Any:
        """Expose the wrapped raw tab while the handle remains valid."""
        return self._ensure_valid()

    @property
    def listen(self) -> DrissionListenerHandle:
        """Return the bounded listener wrapper for this tab."""
        self._ensure_valid()
        return self._listener

    @property
    def url(self) -> str:
        """Return the current page URL as a string."""
        return str(getattr(self._ensure_valid(), "url", "") or "")

    @property
    def title(self) -> str:
        """Return the current page title as a string."""
        return str(getattr(self._ensure_valid(), "title", "") or "")

    @property
    def html(self) -> str:
        """Return the current page HTML as a string."""
        return str(getattr(self._ensure_valid(), "html", "") or "")

    def get(self, url: str, timeout: int = 10, retry: int = 0):
        """Navigate the wrapped tab to a URL."""
        return self._ensure_valid().get(url, timeout=timeout, retry=retry)

    def ele(self, selector: str, timeout: float = 0, index: int = 1) -> Any:
        """Find one element in the wrapped tab."""
        return self._ensure_valid().ele(selector, timeout=timeout, index=index)

    def eles(self, selector: str, timeout: float = 0) -> Any:
        """Find multiple elements in the wrapped tab."""
        return self._ensure_valid().eles(selector, timeout=timeout)

    def refresh(self) -> None:
        """Refresh the wrapped tab when the raw implementation supports it."""
        refresh = getattr(self._ensure_valid(), "refresh", None)
        if callable(refresh):
            refresh()

    def run_js(self, script: str) -> Any:
        """Run JavaScript in the wrapped tab context."""
        runner = getattr(self._ensure_valid(), "run_js", None)
        if not callable(runner):
            raise AttributeError("Wrapped tab does not expose run_js")
        return runner(script)

    def close(self) -> None:
        """Close the tab through its owning session when possible."""
        session = self._session
        if session is not None and hasattr(session, "close_tab"):
            session.close_tab(self.name)
            return
        raw_tab = self._ensure_valid()
        close = getattr(raw_tab, "close", None)
        if callable(close):
            close()
        self.invalidate()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ensure_valid(), name)


def ensure_tab_handle(tab: Any, *, session: Any | None = None, name: str | None = None) -> DrissionTabHandle:
    """Return a stable tab handle, wrapping raw tabs when needed."""
    if isinstance(tab, DrissionTabHandle):
        return tab
    handle_name = name or str(getattr(tab, "name", "") or "<tab>")
    return DrissionTabHandle(tab, name=handle_name, session=session)
