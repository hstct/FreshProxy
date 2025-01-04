import pytest
import requests

from unittest.mock import patch, MagicMock
from freshproxy.app import create_app


@pytest.fixture
def client():
    """
    Pytest fixture to create a test client using the Flask app.
    """
    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client


def test_unsupported_endpoint(client):
    """
    Test that accessing the root without a specific route returns 404.
    """
    response = client.get("/")
    assert response.status_code == 404


@patch("freshproxy.proxy_routes.requests.get")
def test_valid_subscriptions(mock_get, client):
    """
    Test the /subscriptions endpoint.
    """
    # 1) Mock requests.get to return a successful response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"subscriptions": ["Feed1", "Feed2"]}
    mock_get.return_value = mock_response

    # 2) Call a valid endpoint from ALLOWED_ENDPOINTS
    response = client.get("/subscriptions")
    assert response.status_code == 200

    # 3) Check the returned JSON
    data = response.get_json()
    assert "subscriptions" in data
    assert data["subscriptions"] == ["Feed1", "Feed2"]

    # 4) Ensure the mock was called once with expected params
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert "headers" in kwargs
    assert kwargs["params"] == {"output": "json"}
    assert kwargs["timeout"] == 10


@patch("freshproxy.proxy_routes.requests.get")
def test_valid_feed_contents(mock_get, client):
    """
    Test the /feed/<id> endpoint with query parameters.
    """
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"feed": ["Feed1", "Feed2"]}
    mock_get.return_value = mock_response

    feed_id = "40"
    query_param = {"n": "1"}

    response = client.get(f"/feed/{feed_id}", query_string=query_param)

    assert response.status_code == 200
    data = response.get_json()
    assert "feed" in data
    assert data["feed"] == ["Feed1", "Feed2"]

    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert "headers" in kwargs
    assert kwargs["params"] == query_param
    assert kwargs["timeout"] == 10


@patch("freshproxy.proxy_routes.requests.get")
def test_timeout_subscriptions(mock_get, client):
    """
    Test that a timeout in requests.get leads to a 504 response for /subscriptions.
    """
    mock_get.side_effect = requests.Timeout()

    response = client.get("/subscriptions")
    assert response.status_code == 504
    assert "timed out" in response.get_json()["error"]


@patch("freshproxy.proxy_routes.requests.get")
def test_json_decode_error_subscriptions(mock_get, client):
    """
    Test that a JSON decode error leads to a 500 response for /subscriptions.
    """
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Bad JSON format")
    mock_get.return_value = mock_response

    response = client.get("/subscriptions")
    assert response.status_code == 500
    body = response.get_json()
    assert "Failed to decode JSON response" in body["error"]


@patch("freshproxy.proxy_routes.requests.get")
def test_endpoint_with_query_params(mock_get, client):
    """
    Test that an endpoint containing a query param is accepted.
    """
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"subscriptions": ["Feed1", "Feed2"]}
    mock_get.return_value = mock_response
    response = client.get("/subscriptions?output=json")
    assert response.status_code == 200
