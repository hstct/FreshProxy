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

    def _proxy_mock_response(return_value, success=True):
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


def test_aggregated_all_latest(client, mock_requests_get):
    """
    Test the /all-latest aggregator route.
    """
    subscription_response = MagicMock()
    subscription_response.ok = True
    subscription_response.json.return_value = {
        "subscriptions": [
            {
                "id": "feed1",
                "title": "Feed 1",
                "htmlUrl": "https://feed1-url",
                "iconUrl": "https://icon1-url",
                "categories": [{"label": "favs"}],
            },
            {
                "id": "feed2",
                "title": "Feed 2",
                "htmlUrl": "https://feed2-url",
                "iconUrl": "https://icon2-url",
                "categories": [],
            },
        ]
    }

    feed1_response = MagicMock()
    feed1_response.ok = True
    feed1_response.json.return_value = {
        "items": [
            {
                "title": "Feed1 Post Title",
                "published": 1697000000,
                "alternate": [{"href": "https://feed1-post-url"}],
            }
        ]
    }

    feed2_response = MagicMock()
    feed2_response.ok = True
    feed2_response.json.return_value = {
        "items": [
            {
                "title": "Feed2 Post Title",
                "published": 1697100000,
                "alternate": [{"href": "https://feed2-post-url"}],
            }
        ]
    }

    mock_requests_get.side_effect = [
        subscription_response,
        feed1_response,
        feed2_response,
    ]

    response = client.get("/all-latest?n=1&page=1&limit=2")

    assert response.status_code == 200
    data = response.get_json()
    assert "feeds" in data
    assert len(data["feeds"]) == 2

    feed1_data = next((f for f in data["feeds"] if f["id"] == "feed1"), None)
    assert feed1_data is not None
    assert feed1_data["title"] == "Feed 1"
    assert len(feed1_data["items"]) == 1
    assert feed1_data["items"][0]["title"] == "Feed1 Post Title"

    feed2_data = next((f for f in data["feeds"] if f["id"] == "feed2"), None)
    assert feed2_data is not None
    assert feed2_data["title"] == "Feed 2"
    assert len(feed2_data["items"]) == 1
    assert feed2_data["items"][0]["title"] == "Feed2 Post Title"

    calls = mock_requests_get.call_args_list
    assert len(calls) == 3

    assert "subscription/list" in calls[0][0][0]
    assert "/feed/feed1" in calls[1][0][0]
    assert "/feed/feed2" in calls[2][0][0]


def test_aggreated_error_handling(client, mock_requests_get):
    """
    Test aggregator handling a feed fetch error with retries.
    """
    subscription_response = MagicMock()
    subscription_response.ok = True
    subscription_response.json.return_value = {
        "subscriptions": [
            {"id": "feed1", "title": "Feed 1"},
        ]
    }

    fail_response = MagicMock()
    fail_response.raise_for_status.side_effect = requests.RequestException("500 Server Error")
    success_response = MagicMock()
    success_response.ok = True
    success_response.json.return_value = {
        "items": [
            {"title": "Feed1 Post Title", "published": 1697000000},
        ]
    }

    mock_requests_get.side_effect = [
        subscription_response,  # /subscription/list
        fail_response,  # /feed/feed1 attempt #1
        success_response,  # /feed/feed1 attempt #2
    ]

    response = client.get("/all-latest?n=1")
    assert response.status_code == 200
    data = response.get_json()
    assert "feeds" in data

    feed_data = data["feeds"][0]
    assert feed_data["id"] == "feed1"
    # Should have retrieved the item after retry
    assert len(feed_data["items"]) == 1
    assert feed_data["items"][0]["title"] == "Feed1 Post Title"

    calls = mock_requests_get.call_args_list
    assert len(calls) == 3
