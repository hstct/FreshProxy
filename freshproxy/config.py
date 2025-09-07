import os
import logging

from typing import List, Dict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file (if present)
load_dotenv()

# Retrieve environment variables
AUTH_TOKEN: str = os.getenv("FRESHRSS_API_TOKEN", "")
BASE_URL: str = os.getenv("FRESHRSS_BASE_URL", "").rstrip("/")
REQUEST_TIMEOUT: int = int(os.getenv("FRESHPROXY_REQUEST_TIMEOUT", 10))
ALLOWED_ORIGINS_ENV: str = os.getenv("FRESHPROXY_ALLOWED_ORIGINS", "")
ALLOWED_ENDPOINTS: Dict[str, str] = {
    "subscriptions": "subscription/list",
    "feed": "stream/contents/feed",
    "label": "stream/contents/user/-/label",
}

# Split, strip, and filter out empty strings
ALLOWED_ORIGINS: List[str] = [
    origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()
]

# Server config
DEBUG: bool = os.getenv("FRESHPROXY_DEBUG", "False").lower() == "true"
HOST: str = os.getenv("FRESHPROXY_HOST", "0.0.0.0")
PORT: int = int(os.getenv("FRESHPROXY_PORT", 8000))

# Logging config
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL: int = logging.DEBUG if DEBUG else logging.INFO

# Warning if essential environment variable is missing
if not AUTH_TOKEN or not BASE_URL:
    logger.warning(
        "Either FRESHRSS_API_TOKEN or FRESHRSS_BASE_URL is missing. "
        "Proxy may not function correctly."
    )
