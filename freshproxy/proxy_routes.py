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


def get_cache_key(label, n):
    """
    Create a unique cache key for aggregator queries.
    """
    return f"digest|{label}|{n}"


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
        actual_id = actual_id[len("feed/") :]

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
    if feed_id.startswith("feed/"):
        feed_id = feed_id[len("feed/") :]
    return re.fullmatch(r"\d+", feed_id) is not None


@proxy_bp.route("/digest", methods=["GET"])
def get_digest():
    """
    Return a sorted list of the latest items across all feeds (optionally filtered by label).

    Query params:
        - label:    Filter feeds by this label (optional)
        - n:        Number of items to fetch per feed (default=1)
        - page:     1-based index of which "items page" to return (default=1)
        - limit:    How many items per page (default=50)
    """
    label = request.args.get("label", "")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 50))
    n = int(request.args.get("n", 1))

    cache_key = get_cache_key(label, n)

    cached_data = get_cache_value(cache_key)
    if cached_data is not None:
        logger.info(f"Using cached flattened data for cache_key={cache_key}")
        all_items = cached_data
    else:
        logger.info(f"Cache miss for cache_key={cache_key}. Fetching from FreshRSS.")

        # 1) Fetch the subscriptions from FreshRSS
        subscriptions_endpoint = ALLOWED_ENDPOINTS.get("subscriptions", "subscription/list")
        subscriptions_url = f"{BASE_URL}/{subscriptions_endpoint}"
        headers = {"Authorization": f"GoogleLogin auth={AUTH_TOKEN}"}
        sub_params = {"output": "json"}  # FreshRSS expects 'output=json' for JSON responses

        try:
            sub_resp = requests.get(
                subscriptions_url, headers=headers, params=sub_params, timeout=REQUEST_TIMEOUT
            )
            sub_resp.raise_for_status()
            subscriptions_data = sub_resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch subscriptions: {e}")
            return jsonify({"error": "Failed to fetch subscriptions", "details": str(e)}), 502
        except ValueError as e:
            logger.error(f"JSON decode error in subscriptions: {e}")
            return (
                jsonify({"error": "Failed to decode JSON (subscriptions)", "details": str(e)}),
                500,
            )

        # 2) Filter the subscriptions by label if specified
        all_feeds = subscriptions_data.get("subscriptions", [])
        if label:
            all_feeds = [
                feed
                for feed in all_feeds
                if any(cat.get("label") == label for cat in feed.get("categories", []))
            ]
        logger.info(f"Found {len(all_feeds)} feeds after label filtering.")

        # 3) Flatten items from each feed into a single list
        all_items = []

        def process_feed(feed):
            feed_id = feed.get("id")
            if not feed_id:
                logger.warning(f"Skipping feed with no id: {feed}")
                return []

            if not is_valid_feed_id(feed_id):
                logger.warning(f"Skipping feed with invalid id: {feed_id}")
                return []

            items = fetch_feed_posts(feed_id, n=n, retry_attempts=2)
            # If fetch_feed_posts returns a dict with "error", handle gracefully
            if isinstance(items, dict) and "error" in items:
                logger.warning(f"Error while fetching feed {feed_id}: {items['error']}")
                return []

            if not isinstance(items, list):
                logger.warning(
                    f"Expected list of items, got {type(items)}. Skipping feed {feed_id}"
                )
                return []

            for item in items:
                item["feedId"] = feed_id
                item["feedTitle"] = feed.get("title", "")
                item["feedHtmlUrl"] = feed.get("htmlUrl")
                item["feedIconUrl"] = feed.get("iconUrl")
            return items

        max_workers = min(10, len(all_feeds))  # limit concurrency
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_feed = {executor.submit(process_feed, f): f for f in all_feeds}
            for future in as_completed(future_to_feed):
                feed_items = future.result()
                all_items.extend(feed_items)

        # 4) Sort the flattened list by `published` descending
        all_items.sort(key=lambda x: x.get("published", 0), reverse=True)

        # 5) Store in cache for future requests
        set_cache_value(cache_key, all_items)

    # 6) Pagination: slice the all_items list
    offset = max(0, (page - 1) * limit)
    paginated_items = all_items[offset : offset + limit]

    # 7) Construct the response
    response_data = {
        "items": paginated_items,
        "page": page,
        "limit": limit,
        "totalItems": len(all_items),
    }

    return jsonify(response_data)
