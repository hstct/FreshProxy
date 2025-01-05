import pytest
import requests

from unittest.mock import patch, MagicMock
from freshproxy.app import create_app
from freshproxy.config import AUTH_TOKEN, REQUEST_TIMEOUT


@pytest.fixture
def client(monkeypatch):
    """
    Pytest fixture to create a test client using the Flask app.
    """
    monkeypatch.setenv("FRESHRSS_API_TOKEN", "test-token")
    monkeypatch.setenv("FRESHRSS_BASE_URL", "https://freshrss.example.com/greader.php")
    monkeypatch.setenv(
        "FRESHPROXY_ALLOWED_ORIGINS",
        "http://localhost:3000,https://test.com,https://proxy.example.com",
    )
    monkeypatch.setenv("FRESHPROXY_DEBUG", "True")
    monkeypatch.setenv("FRESHPROXY_REQUEST_TIMEOUT", 5)

    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_requests_get():
    """
    Pytest fixture to mock requests.get.
    """
    with patch("freshproxy.proxy_routes.requests.get") as mock_get:
        yield mock_get


@pytest.fixture
def proxy_mock_response():
    """
    Pytest fixture to set up mock responses.
    """
    def _proxy_mock_response(return_value, success = True):
        mock_response = MagicMock()
        mock_response.ok = success
        mock_response.json.return_value = return_value
        return mock_response

    return _proxy_mock_response


def test_unsupported_endpoint(client):
    """
    Test that accessing the root without a specific route returns 404.
    """
    response = client.get("/")
    assert response.status_code == 404


def test_valid_subscriptions(mock_requests_get, proxy_mock_response, client):
    """
    Test the /subscriptions endpoint.
    """
    mock_requests_get.return_value = proxy_mock_response({"subscriptions": ["Feed1", "Feed2"]})

    response = client.get("/subscriptions")
    assert response.status_code == 200

    data = response.get_json()
    assert "subscriptions" in data
    assert data["subscriptions"] == ["Feed1", "Feed2"]

    mock_requests_get.assert_called_once()
    _, kwargs = mock_requests_get.call_args
    assert "headers" in kwargs
    assert kwargs["headers"] == {"Authorization": f"GoogleLogin auth={AUTH_TOKEN}"}
    assert kwargs["params"] == {"output": "json"}
    assert kwargs["timeout"] == REQUEST_TIMEOUT


def test_valid_feed_contents(mock_requests_get, proxy_mock_response, client):
    """
    Test the /feed/<id> endpoint with query parameters.
    """
    mock_requests_get.return_value = proxy_mock_response({"feed": ["Feed1", "Feed2"]})

    feed_id = "40"
    query_param = {"n": "1"}

    response = client.get(f"/feed/{feed_id}", query_string=query_param)

    assert response.status_code == 200
    data = response.get_json()
    assert "feed" in data
    assert data["feed"] == ["Feed1", "Feed2"]

    mock_requests_get.assert_called_once()
    _, kwargs = mock_requests_get.call_args
    assert "headers" in kwargs
    assert kwargs["params"] == query_param
    assert kwargs["timeout"] == REQUEST_TIMEOUT


def test_timeout_subscriptions(mock_requests_get, client):
    """
    Test that a timeout in requests.get leads to a 504 response for /subscriptions.
    """
    mock_requests_get.side_effect = requests.Timeout()

    response = client.get("/subscriptions")
    assert response.status_code == 504
    assert "timed out" in response.get_json()["error"]


def test_json_decode_error_subscriptions(mock_requests_get, client):
    """
    Test that a JSON decode error leads to a 500 response for /subscriptions.
    """
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Bad JSON format")
    mock_requests_get.return_value = mock_response

    response = client.get("/subscriptions")
    assert response.status_code == 500
    body = response.get_json()
    assert "Failed to decode JSON response" in body["error"]


def test_subscriptions_accepts_query_params(mock_requests_get, proxy_mock_response, client):
    """
    Test that the /subscriptions endpoint accepts and correctly forwards query parameters.
    """
    mock_requests_get.return_value = proxy_mock_response({"subscriptions": ["Feed1", "Feed2"]})

    response = client.get("/subscriptions?output=json")
    assert response.status_code == 200

    data = response.get_json()
    assert "subscriptions" in data

    mock_requests_get.assert_called_once()
    _, kwargs = mock_requests_get.call_args
    assert "headers" in kwargs
    assert kwargs["params"] == {"output": "json"}
    assert kwargs["timeout"] == REQUEST_TIMEOUT


def test_invalid_feed_id(mock_requests_get, client):
    """
    Test that an invalid feed_id format returns a 400 Bad Request.
    """
    invalid_feed_id = "invalid123"

    response = client.get(f"/feed/{invalid_feed_id}")
    assert response.status_code == 400
    body = response.get_json()
    assert "Invalid feed_id format" in body["error"]

    mock_requests_get.assert_not_called()
