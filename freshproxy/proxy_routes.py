import logging
import requests

from typing import Union, Tuple
from flask import Blueprint, request, jsonify, Response
from flask_cors import cross_origin
from freshproxy.config import AUTH_TOKEN, BASE_URL, ALLOWED_ENDPOINTS, ALLOWED_ORIGINS

proxy_bp = Blueprint("proxy_bp", __name__)


def proxy_request(endpoint: str, params: dict) -> Union[Response, Tuple[Response, int]]:
    """
    Helper function to proxy requests to FrehsRSS.
    """
    url = f"{BASE_URL}/{endpoint}"
    headers = {"Authorization": f"GoogleLogin auth={AUTH_TOKEN}"}

    try:
        logging.info(f"Fetching data from: {url} with param: {params}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)

    except requests.Timeout:
        logging.error("Request to FreshRSS GReader API timed out")
        return jsonify({"error": "Request to FreshRSS GReader API timed out"}), 504

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return jsonify({"error": "Request error", "details": str(e)}), 502

    except ValueError as e:
        logging.error(f"JSON decode error: {e}")
        return (
            jsonify({"error": "Failed to decode JSON response", "details": str(e)}),
            500,
        )


@proxy_bp.route("/subscriptions", methods=["GET"])
@cross_origin(origins=ALLOWED_ORIGINS)
def get_subscriptions() -> Union[Response, Tuple[Response, int]]:
    """
    Proxy endpoint for /subscriptions -> FreshRSS subscription/list
    """
    endpoint = ALLOWED_ENDPOINTS.get("subscriptions")
    if not endpoint:
        logging.error("FreshRSS endpoint for 'subscriptions' not configured.")
        return jsonify({"error": "Internal server error"}), 500

    params = request.args.to_dict()
    params.update({"output": "json"})

    return proxy_request(endpoint, params)


@proxy_bp.route("/feeds/<feed_id>", methods=["GET"])
@cross_origin(origins=ALLOWED_ORIGINS)
def get_feed_contents(feed_id: str) -> Union[Response, Tuple[Response, int]]:
    """
    Proxy endpoint for /feeds/<id> -> FreshRSS stream/contents/feed/<id>
    """
    base_endpoint = ALLOWED_ENDPOINTS.get("feeds")
    if not base_endpoint:
        logging.error("FreshRSS base endpoint for 'feeds' not configured.")
        return jsonify({"error": "Internal server error"}), 500

    endpoint = f"{base_endpoint}/{feed_id}"
    params = request.args.to_dict()

    return proxy_request(endpoint, params)
