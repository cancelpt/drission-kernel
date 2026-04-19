"""Tests for standalone kernel bootstrap configuration."""

from __future__ import annotations

from drission_kernel.session import BrowserBootstrapConfig


def test_browser_bootstrap_config_has_standalone_defaults() -> None:
    config = BrowserBootstrapConfig()

    assert config.language == "zh-CN"
    assert config.proxy is None
    assert str(config.download_path)
    assert str(config.user_data_dir)
