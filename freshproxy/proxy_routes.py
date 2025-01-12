import logging
import time
import re
import requests

from typing import Union, Tuple
from flask import Blueprint, request, jsonify, Response
from concurrent.futures import ThreadPoolExecutor, as_completed

from freshproxy.config import AUTH_TOKEN, BASE_URL, ALLOWED_ENDPOINTS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)
proxy_bp = Blueprint("proxy_bp", __name__)


AGGREGATOR_CACHE = {}
CACHE_TTL_SECONDS = 300


def get_cache_key(label, page, limit, n):
    """
    Create a unique cache key for aggregator queries.
    """
    return f"all-latest|{label}|{page}|{limit}|{n}"


def set_cache_value(cache_key, value):
    """
    Store a (timestamp, data) tuple in the global aggregator cache.
    """
    AGGREGATOR_CACHE[cache_key] = (time.time(), value)


def get_cache_value(cache_key):
    """
    Retrieve the cached value if it's not expired; otherwise return None.
    """
    cache_item = AGGREGATOR_CACHE.get(cache_key)
    if not cache_item:
        return None
    cached_time, data = cache_item
    if time.time() - cached_time > CACHE_TTL_SECONDS:
        # expired
        AGGREGATOR_CACHE.pop(cache_key, None)
        return None
    return data


def fetch_feed_posts(feed_id, n=1, retry_attempts=2):
    """
    Fetch up to 'n' latest posts for a single feed, with retry logic.
    Returns a dict with feed info or an error message.
    """
    feed_endpoint = ALLOWED_ENDPOINTS.get("feed", "stream/contents/feed")
    actual_id = feed_id
    if actual_id.startswith("feed/"):
        actual_id = actual_id[len("feed/"):]

    feed_url = f"{BASE_URL}/{feed_endpoint}/{actual_id}"
    headers = {"Authorization": f"GoogleLogin auth={AUTH_TOKEN}"}
    params = {"n": n}

    for attempt in range(retry_attempts + 1):
        try:
            resp = requests.get(feed_url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            data = resp.json()
            items = data.get("items", [])
            return items

        except requests.Timeout:
            logger.warning(f"Timeout fetching feed_id={feed_id}, attempt={attempt}")
            if attempt == retry_attempts:
                return {"error": "Timeout after retries"}
        except requests.RequestException as e:
            logger.warning(f"Request error fetching feed_id={feed_id}, attempt={attempt}: {e}")
            if attempt == retry_attempts:
                return {"error": str(e)}
        except ValueError as e:
            logger.warning(f"JSON decode error feed_id={feed_id}, attempt={attempt}: {e}")
            if attempt == retry_attempts:
                return {"error": f"JSON decode error: {e}"}

    return {"error": "Unknown fetch error"}


def proxy_request(endpoint: str, params: dict) -> Union[Response, Tuple[Response, int]]:
    """
    Helper function to proxy requests to FrehsRSS.

    Args:
        endpoint (str): The FreshRSS endpoint to proxy to.
        params (dict): Query parameters to include in the request.

    Returns:
        Union[Response, Tuple[Response, int]]: Flask Response object or a tuple of Response
                                               and status code.
    """
    url = f"{BASE_URL}/{endpoint}"
    headers = {"Authorization": f"GoogleLogin auth={AUTH_TOKEN}"}

    try:
        logger.info(f"Fetching data from: {url} with params: {params}")
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)

    except requests.Timeout:
        logger.error("Request to FreshRSS GReader API timed out")
        return jsonify({"error": "Request to FreshRSS GReader API timed out"}), 504

    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        return jsonify({"error": "Request error", "details": str(e)}), 502

    except ValueError as e:
        logger.error(f"JSON decode error: {e}")
        return (
            jsonify({"error": "Failed to decode JSON response", "details": str(e)}),
            500,
        )


def is_valid_feed_id(feed_id: str) -> bool:
    """
    Validates the format of the feed_id.

    Args:
        feed_id (str): The feed ID to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    return re.fullmatch(r"\d+", feed_id) is not None


@proxy_bp.route("/subscriptions", methods=["GET"])
def get_subscriptions() -> Union[Response, Tuple[Response, int]]:
    """
    Proxy endpoint for /subscriptions -> FreshRSS subscription/list

    Returns:
        Union[Response, Tuple[Response, int]]: JSON response or error message with status code.
    """
    endpoint = ALLOWED_ENDPOINTS.get("subscriptions")
    if not endpoint:
        logger.error("FreshRSS endpoint for 'subscriptions' not configured.")
        return jsonify({"error": "Internal server error"}), 500

    params = request.args.to_dict()
    params.update({"output": "json"})

    return proxy_request(endpoint, params)


@proxy_bp.route("/feed/<feed_id>", methods=["GET"])
def get_feed_contents(feed_id: str) -> Union[Response, Tuple[Response, int]]:
    """
    Proxy endpoint for /feed/<id> -> FreshRSS stream/contents/feed/<id>

    Args:
        feed_id (str): The ID of the feed to retrieve contents for.

    Returns:
        Union[Response, Tuple[Response, int]]: JSON response or error message with status code.
    """
    if not is_valid_feed_id(feed_id):
        logger.warning(f"Invalid feed_id format received: {feed_id}")
        return jsonify({"error": "Invalid feed_id format"}), 400

    base_endpoint = ALLOWED_ENDPOINTS.get("feed")
    if not base_endpoint:
        logger.error("FreshRSS base endpoint for 'feed' not configured.")
        return jsonify({"error": "Internal server error"}), 500

    endpoint = f"{base_endpoint}/{feed_id}"
    params = request.args.to_dict()

    return proxy_request(endpoint, params)


@proxy_bp.route("/all-latest", methods=["GET"])
def get_all_latest():
    """
    Aggregates the latest posts from all (or labeled) feeds in one request.
    - Optional query params:
        ?label=someLabel    -> filter subscriptions by that label
        ?page=1             -> which page of feeds to return (for feed-level pagination)
        ?limit=50           -> how many feeds to return per page
        ?n=1                -> how many items per feed (default 1)
    """
    # Parse query params
    label = request.args.get("label", "")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 50))
    n = int(request.args.get("n", 1))

    # Check cache
    cache_key = get_cache_key(label, page, limit, n)
    cached_data = get_cache_value(cache_key)
    if cached_data:
        logger.info(f"Aggregator cache hit for {cache_key}")
        return jsonify(cached_data)

    # Fetch subscriptions
    subscriptions_endpoint = ALLOWED_ENDPOINTS.get("subscriptions", "subscription/list")
    subscription_url = f"{BASE_URL}/{subscriptions_endpoint}"
    headers = {"Authorization": f"GoogleLogin auth={AUTH_TOKEN}"}
    sub_params = {"output": "json"}

    try:
        logger.info("Fetching subscription list for aggregator.")
        sub_resp = requests.get(
            subscription_url, headers=headers, params=sub_params, timeout=REQUEST_TIMEOUT
        )
        sub_resp.raise_for_status()
        subscriptions_data = sub_resp.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch subscriptions: {e}")
        return jsonify({"error": "Failed to fetch subscriptions", "details": str(e)}), 502
    except ValueError as e:
        logger.error(f"JSON decode error in subscriptions: {e}")
        return jsonify({"error": "Failed to decode JSON (subscriptions)", "details": str(e)}), 500

    # Filter feeds
    all_feeds = subscriptions_data.get("subscriptions", [])
    if label:
        all_feeds = [
            feed
            for feed in all_feeds
            if any(cat.get("label") == label for cat in feed.get("categories", []))
        ]

    logger.info(f"Found total {len(all_feeds)} feeds after label filtering.")

    # Apply pagination
    offset = max(0, (page - 1) * limit)
    paginated_feeds = all_feeds[offset : offset + limit]
    logger.info(f"Pagination: returning feeds {offset} to {offset+limit-1} (inclusive).")

    # Fetch in parallel
    results = []
    max_workers = min(10, len(paginated_feeds))  # limit concurrency

    def process_feed(feed):
        feed_id = feed.get("id")
        if not feed_id:
            return {"error": "No feed ID found"}

        items = fetch_feed_posts(feed_id, n=n, retry_attempts=2)
        if isinstance(items, dict) and "error" in items:
            return {
                "id": feed_id,
                "title": feed.get("title", ""),
                "htmlUrl": feed.get("htmlUrl"),
                "iconUrl": feed.get("iconUrl"),
                "items": [],
                "error": items["error"],
            }

        return {
            "id": feed_id,
            "title": feed.get("title", ""),
            "htmlUrl": feed.get("htmlUrl"),
            "iconUrl": feed.get("iconUrl"),
            "items": items,
        }

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(process_feed, f): f for f in paginated_feeds}

        for future in as_completed(future_map):
            feed_data = future.result()
            results.append(feed_data)

    # Build final JSON
    response_data = {
        "feeds": results,
        "page": page,
        "limit": limit,
        "totalFeeds": len(all_feeds),
    }

    # Set cache
    set_cache_value(cache_key, response_data)

    return jsonify(response_data)
