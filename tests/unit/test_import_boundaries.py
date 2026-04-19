"""Import-boundary tests for the standalone kernel package."""

from __future__ import annotations

from pathlib import Path


def test_kernel_source_tree_exists() -> None:
    src_dir = Path(__file__).resolve().parents[2] / "src" / "drission_kernel"

    assert src_dir.exists()


def test_kernel_source_does_not_import_blocked_external_modules() -> None:
    src_dir = Path(__file__).resolve().parents[2] / "src" / "drission_kernel"
    assert src_dir.exists()
    blocked_modules = ("site" + "pilot",)

    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for blocked_module in blocked_modules:
            assert blocked_module not in content, f"Kernel file depends on a blocked external module: {py_file}"
