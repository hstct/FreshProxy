import os
import logging

from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

AUTH_TOKEN = os.getenv("FRESHRSS_API_TOKEN", "")
BASE_URL = os.getenv("FRESHRSS_BASE_URL", "").rstrip("/")
ALLOWED_ORIGINS = os.getenv("FRESHPROXY_ALLOWED_ORIGINS", "")
ALLOWED_ENDPOINTS = {"subscriptions": "subscription/list", "feed": "stream/contents/feed"}

ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS.split(",")]

DEBUG = os.getenv("FRESHPROXY_DEBUG", "False").lower() == "true"
HOST = os.getenv("FRESHPROXY_HOST", "0.0.0.0")
PORT = int(os.getenv("FRESHPROXY_PORT", 8000))

if not AUTH_TOKEN or not BASE_URL:
    logging.warning(
        "Either FRESHRSS_API_TOKEN or FRESHRSS_BASE_URL is missing. "
        "Proxy may not function correctly."
    )
