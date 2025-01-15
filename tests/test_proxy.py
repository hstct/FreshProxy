import pytest
import requests

from unittest.mock import patch, MagicMock
from freshproxy.app import create_app
from freshproxy.proxy_routes import AGGREGATOR_CACHE


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
    monkeypatch.setenv("FRESHPROXY_REQUEST_TIMEOUT", "5")

    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_aggregator_cache():
    """
    This fixture runs automatically before each test, ensuring
    the aggregator cache is empty so tests don't interfere with each other.
    """
    AGGREGATOR_CACHE.clear()
    yield
    AGGREGATOR_CACHE.clear()


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


def test_aggregated_digest(client, mock_requests_get):
    """
    Test the /digest aggregator route, ensuring we get a flat list of items
    sorted by 'published' descending, along with pagination metadata.
    """
    subscription_response = MagicMock()
    subscription_response.ok = True
    subscription_response.json.return_value = {
        "subscriptions": [
            {
                "id": "feed/1",
                "title": "Feed 1",
                "htmlUrl": "https://feed1-url",
                "iconUrl": "https://icon1-url",
                "categories": [{"label": "favs"}],
            },
            {
                "id": "feed/2",
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

    response = client.get("/digest?n=1&page=1&limit=2")
    assert response.status_code == 200

    data = response.get_json()
    assert "items" in data, "Response must contain 'items' key"
    assert len(data["items"]) == 2

    assert data["items"][0]["title"] == "Feed2 Post Title"
    assert data["items"][0]["feedId"] == "feed/2"
    assert data["items"][1]["title"] == "Feed1 Post Title"
    assert data["items"][1]["feedId"] == "feed/1"

    assert data["page"] == 1
    assert data["limit"] == 2
    assert data["totalItems"] == 2

    item0 = data["items"][0]
    assert item0["feedTitle"] == "Feed 2"
    assert item0["feedHtmlUrl"] == "https://feed2-url"
    assert item0["feedIconUrl"] == "https://icon2-url"


def test_aggreated_error_handling(client, mock_requests_get):
    """
    Test aggregator handling a feed fetch error with retries.
    Ensures that if one feed fails, we still get items from the other feeds,
    or handle partial data gracefully.
    """
    subscription_response = MagicMock()
    subscription_response.ok = True
    subscription_response.json.return_value = {
        "subscriptions": [
            {"id": "feed/1", "title": "Feed 1"},
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
        subscription_response,
        fail_response,
        success_response,
    ]

    response = client.get("/digest?n=1")
    assert response.status_code == 200

    data = response.get_json()
    assert "items" in data
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["title"] == "Feed1 Post Title"
    assert item["feedId"] == "feed/1"

    assert data["page"] == 1
    assert data["limit"] == 50
    assert data["totalItems"] == 1

    calls = mock_requests_get.call_args_list
    assert len(calls) == 3


def test_invalid_feed_id(client, mock_requests_get):
    """
    Test that an invalid feed ID in the subscription list is handled gracefully
    by the aggregator, e.g., skipped or logged as a warning without crashing.
    """
    subscription_response = MagicMock()
    subscription_response.ok = True
    subscription_response.json.return_value = {
        "subscriptions": [
            {
                "id": "feed/1",
                "title": "Valid Feed",
                "htmlUrl": "https://valid-feed-url",
                "iconUrl": "https://valid-feed-icon",
            },
            {
                "id": "feed/abc",  # This is the invalid one
                "title": "Invalid Feed",
                "htmlUrl": "https://invalid-feed-url",
                "iconUrl": "https://invalid-feed-icon",
            },
        ]
    }

    valid_feed_response = MagicMock()
    valid_feed_response.ok = True
    valid_feed_response.json.return_value = {
        "items": [
            {
                "title": "Valid Feed Post",
                "published": 1697000000,
            }
        ]
    }

    mock_requests_get.side_effect = [
        subscription_response,
        valid_feed_response,
    ]

    response = client.get("/digest?n=1")
    assert response.status_code == 200

    data = response.get_json()
    assert "items" in data
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["title"] == "Valid Feed Post"
    assert item["feedId"] == "feed/1"

    assert data["totalItems"] == 1

    calls = mock_requests_get.call_args_list
    assert len(calls) == 2


def test_pagination_in_digest(client, mock_requests_get):
    """
    Test that pagination (page/limit) is properly applied to the global
    sorted list of items.
    """
    subscription_response = MagicMock()
    subscription_response.ok = True
    subscription_response.json.return_value = {
        "subscriptions": [
            {"id": "feed/1", "title": "Feed 1"},
            {"id": "feed/2", "title": "Feed 2"},
        ]
    }

    feed1_response = MagicMock()
    feed1_response.ok = True
    feed1_response.json.return_value = {
        "items": [
            {
                "title": "Feed1 Post A",
                "published": 1697100002,
            },
            {
                "title": "Feed1 Post B",
                "published": 1697100001,
            },
        ]
    }

    feed2_response = MagicMock()
    feed2_response.ok = True
    feed2_response.json.return_value = {
        "items": [
            {
                "title": "Feed2 Post A",
                "published": 1697100004,
            },
            {
                "title": "Feed2 Post B",
                "published": 1697100003,
            },
        ]
    }

    mock_requests_get.side_effect = [
        subscription_response,
        feed1_response,
        feed2_response,
    ]

    response_page1 = client.get("/digest?n=2&page=1&limit=2")
    assert response_page1.status_code == 200
    data_page1 = response_page1.get_json()
    assert len(data_page1["items"]) == 2
    assert data_page1["items"][0]["title"] == "Feed2 Post A"
    assert data_page1["items"][1]["title"] == "Feed2 Post B"
    assert data_page1["totalItems"] == 4
    assert data_page1["page"] == 1
    assert data_page1["limit"] == 2

    response_page2 = client.get("/digest?n=2&page=2&limit=2")
    assert response_page2.status_code == 200
    data_page2 = response_page2.get_json()
    assert len(data_page2["items"]) == 2
    assert data_page2["items"][0]["title"] == "Feed1 Post A"
    assert data_page2["items"][1]["title"] == "Feed1 Post B"
    assert data_page2["page"] == 2
    assert data_page2["limit"] == 2
    assert data_page2["totalItems"] == 4


def test_caching_digest(client, mock_requests_get):
    """
    Test that calling /digest with the same label/n parameters multiple times
    uses cached data on the second request and does NOT re-fetch feeds from FreshRSS.
    """
    subscription_response = MagicMock()
    subscription_response.ok = True
    subscription_response.json.return_value = {
        "subscriptions": [
            {"id": "feed/1", "title": "Feed 1"},
        ]
    }

    feed1_response = MagicMock()
    feed1_response.ok = True
    feed1_response.json.return_value = {
        "items": [
            {
                "title": "Feed1 Cached Post",
                "published": 1697000000,
            }
        ]
    }

    mock_requests_get.side_effect = [
        subscription_response,
        feed1_response,
    ]

    response = client.get("/digest?n=1")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Feed1 Cached Post"
    assert data["totalItems"] == 1

    calls_after_first = mock_requests_get.call_args_list
    assert len(calls_after_first) == 2

    response_cached = client.get("/digest?n=1")
    assert response_cached.status_code == 200
    data_cached = response_cached.get_json()
    assert len(data_cached["items"]) == 1
    assert data_cached["items"][0]["title"] == "Feed1 Cached Post"

    calls_after_second = mock_requests_get.call_args_list
    assert (
        len(calls_after_second) == 2
    ), "No new requests should be made on the second call if data was cached."
