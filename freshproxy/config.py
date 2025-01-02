import os
import logging

AUTH_TOKEN = os.environ.get("FRESHRSS_API_TOKEN", "")
BASE_URL = os.environ.get("FRESHRSS_BASE_URL", "").rstrip("/")

if not AUTH_TOKEN or not BASE_URL:
    logging.warning(
        "Either FRESHRSS_API_TOKEN or FRESHRSS_BASE_URL is missing. "
        "Proxy may not function correctly."
    )

ALLOWED_ENDPOINTS = {
    "subscription/list",
    "stream/contents",
    "marker/tag/lists",
}

ALLOWED_ORIGINS = ["http://localhost:3000", "https://mydomain.com"]
