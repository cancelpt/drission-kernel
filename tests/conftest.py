"""Pytest bootstrap for the standalone drission-kernel repository."""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    src_dir = root_dir / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
