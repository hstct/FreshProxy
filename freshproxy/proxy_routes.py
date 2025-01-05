import logging
import requests

from typing import Union, Tuple
from flask import Blueprint, request, jsonify, Response

from freshproxy.config import AUTH_TOKEN, BASE_URL, ALLOWED_ENDPOINTS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

proxy_bp = Blueprint("proxy_bp", __name__)


def proxy_request(endpoint: str, params: dict) -> Union[Response, Tuple[Response, int]]:
    """
    Helper function to proxy requests to FrehsRSS.

    Args:
        endpoint (str): The FreshRSS endpoint to proxy to.
        params (dict): Query parameters to include in the request.

    Returns:
        Union[Response, Tuple[Response, int]]: Flask Response object or a tuple of Response and status code.
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
    base_endpoint = ALLOWED_ENDPOINTS.get("feed")
    if not base_endpoint:
        logger.error("FreshRSS base endpoint for 'feed' not configured.")
        return jsonify({"error": "Internal server error"}), 500

    endpoint = f"{base_endpoint}/{feed_id}"
    params = request.args.to_dict()

    return proxy_request(endpoint, params)
