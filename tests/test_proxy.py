import pytest
import requests

from unittest.mock import patch, MagicMock
from frsshproxy.app import create_app


@pytest.fixture
def client():
    """
    Pytest fixture to create a test client using the Flask app.
    """
    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client


def test_missing_endpoint_param(client):
    """
    If we don't provide ?endpoint=, we expect a 400 error.
    """
    response = client.get("/")
    assert response.status_code == 400
    assert "No endpoint specified" in response.get_json()["error"]


def test_disallowed_endpoint(client):
    """
    If we pass an endpoint not in the allowed set, we expect 403.
    """
    response = client.get("/?endpoint=evil")
    assert response.status_code == 403
    assert "not allowed" in response.get_json()["error"]


@patch("frsshproxy.proxy_routes.requests.get")
def test_valid_endpoint(mock_get, client):
    """
    Test a happy path scenario where requests.get returns a 200 with valid JSON.
    """
    # 1) Mock requests.get to return a successful response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"subscriptions": ["Feed1", "Feed2"]}
    mock_get.return_value = mock_response

    # 2) Call a valid endpoint from ALLOWED_ENDPOINTS
    response = client.get("/?endpoint=subscription/list")
    assert response.status_code == 200

    # 3) Check the returned JSON
    data = response.get_json()
    assert "subscriptions" in data
    assert data["subscriptions"] == ["Feed1", "Feed2"]

    # 4) Ensure the mock was called once with expected params
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert "headers" in kwargs
    assert kwargs["timeout"] == 10


@patch("frsshproxy.proxy_routes.requests.get")
def test_timeout(mock_get, client):
    """
    Test that a timeout in requests.get leads to a 504 response.
    """
    mock_get.side_effect = requests.Timeout()

    response = client.get("/?endpoint=subscription/list")
    assert response.status_code == 504
    assert "timed out" in response.get_json()["error"]


@patch("frsshproxy.proxy_routes.requests.get")
def test_json_decode_error(mock_get, client):
    """
    Test that a JSON decode error leads to a 500 response.
    """
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Bad JSON format")
    mock_get.return_value = mock_response

    response = client.get("/?endpoint=subscription/list")
    assert response.status_code == 500
    body = response.get_json()
    assert "Failed to decode JSON response" in body["error"]
