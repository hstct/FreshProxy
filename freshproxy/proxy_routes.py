import logging
import requests

from flask import Blueprint, request, jsonify
from freshproxy.config import AUTH_TOKEN, BASE_URL, ALLOWED_ENDPOINTS

proxy_bp = Blueprint("proxy_bp", __name__)


def is_endpoint_allowed(endpoint: str) -> bool:
    return endpoint in ALLOWED_ENDPOINTS


@proxy_bp.route("/", methods=["GET"])
def proxy():
    endpoint = request.args.get("endpoint")
    if not endpoint:
        return (
            jsonify({"error": "No endpoint specified. Use ?endpoint=<your-endpoint>"}),
            400,
        )

    if not is_endpoint_allowed(endpoint):
        logging.error(f"Endpoint '{endpoint}' is not allowed.")
        return jsonify({"error": f"Endpoint '{endpoint}' not allowed"}), 403

    # Construct the URL safely
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"GoogleLogin auth={AUTH_TOKEN}"}

    try:
        logging.info(f"Fetching data from: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)

    except requests.Timeout:
        logging.error("Request to FreshRSS API timed out")
        return jsonify({"error": "Request to FreshRSS API timed out"}), 504

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return jsonify({"error": "Request error", "details": str(e)}), 502

    except ValueError as e:
        logging.error(f"JSON decode error: {e}")
        return (
            jsonify({"error": "Failed to decode JSON response", "details": str(e)}),
            500,
        )
