import os
import importlib
import logging


def test_missing_env_vars(caplog):
    """
    Ensure that if environment vars are missing, we log a warning.
    """
    # 1) Clear environment variables
    old_token = os.environ.pop("FRESHRSS_API_TOKEN", None)
    old_base = os.environ.pop("FRESHRSS_BASE_URL", None)

    with caplog.at_level(logging.WARNING):
        # 2) Reload the config module
        import freshproxy.config

        importlib.reload(freshproxy.config)

        # 3) Check if a warning was logged
        assert "Proxy may not function correctly" in caplog.text

    # 4) Restore environment
    if old_token:
        os.environ["FRESHRSS_API_TOKEN"] = old_token
    if old_base:
        os.environ["FRESHRSS_BASE_URL"] = old_base

    # 5) Reload again to restore original state
    importlib.reload(freshproxy.config)
