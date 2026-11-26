"""Настройки приложения."""

from testlab.config.app_config import AppConfig


def test_default_upload_limit():
    assert AppConfig().uploads_max_bytes == 10 * 1024 * 1024


def test_upload_limit_from_env(monkeypatch):
    monkeypatch.setenv("UPLOADS_MAX_BYTES", "1024")

    assert AppConfig().uploads_max_bytes == 1024
