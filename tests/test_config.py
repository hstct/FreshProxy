import importlib
import logging


def test_missing_env_vars(monkeypatch, caplog):
    """
    Ensure that if environment vars are missing, we log a warning.
    """
    monkeypatch.delenv("FRESHRSS_API_TOKEN", raising=False)
    monkeypatch.delenv("FRESHRSS_BASE_URL", raising=False)

    with caplog.at_level(logging.WARNING):
        import freshproxy.config
        importlib.reload(freshproxy.config)

        assert "Proxy may not function correctly" in caplog.text


def test_missing_api_token(monkeypatch, caplog):
    """
    Ensure that if FRESHRSS_API_TOKEN is missing, a warning is logged.
    """
    monkeypatch.delenv("FRESHRSS_API_TOKEN", raising=False)

    with caplog.at_level(logging.WARNING):
        import freshproxy.config
        importlib.reload(freshproxy.config)

        assert "Proxy may not function correctly" in caplog.text


def test_missing_base_url(monkeypatch, caplog):
    """
    Ensure that if FRESHRSS_BASE_URL is missing, a warning is logged.
    """
    monkeypatch.delenv("FRESHRSS_BASE_URL", raising=False)

    with caplog.at_level(logging.WARNING):
        import freshproxy.config
        importlib.reload(freshproxy.config)

        assert "Proxy may not function correctly" in caplog.text


def test_allowed_origins_parsing(monkeypatch):
    """
    Test that ALLOWED_ORIGINS are correctly parsed and empty strings are excluded.
    """
    monkeypatch.setenv(
        "FRESHPROXY_ALLOWED_ORIGINS",
        "http://localhost:3000, , https://test.com, ,https://proxy.example.com",
    )

    import freshproxy.config
    importlib.reload(freshproxy.config)

    expected_origins = [
        "http://localhost:3000",
        "https://test.com",
        "https://proxy.example.com",
    ]
    assert freshproxy.config.ALLOWED_ORIGINS == expected_origins


def test_default_values(monkeypatch):
    """
    Test that default values are set correctly when environment variables are missing.
    """
    monkeypatch.delenv("FRESHPROXY_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("FRESHPROXY_DEBUG", raising=False)
    monkeypatch.delenv("FRESHPROXY_HOST", raising=False)
    monkeypatch.delenv("FRESHPROXY_PORT", raising=False)

    import freshproxy.config
    importlib.reload(freshproxy.config)

    assert freshproxy.config.ALLOWED_ORIGINS == []
    assert freshproxy.config.DEBUG is False
    assert freshproxy.config.HOST == "0.0.0.0"
    assert freshproxy.config.PORT == 8000
