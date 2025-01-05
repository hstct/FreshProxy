# FreshProxy

A **Flask**-based proxy for [FreshRSS](https://github.com/FreshRSS/FreshRSS) that securely forwards specific API requests, eliminating the need for dynamic query parameters. Configurable via environment variables (or a `.env` file).

## Overview

**FreshProxy** acts as a dedicated **HTTP proxy** for specific **FreshRSS** endpoints, enhancing security and simplifying request structures. By using dedicated proxy endpoints, you eliminate the need for dynamic query parameters, reducing potential attack vectors and improving clarity.

## Features

- **Dedicated Proxy Endpoints**:
    - `/subscriptions` -> `subscription/list`.
    - `/feed/<id>` -> `stream/contents/feed/<id>`.
- **CORS** restrictions to only allow certain origins.
- **Timeout** and error handling for upstream requests.
- **Environment-based configuration** (via `.env` or standard env vars).
- **Docker Support** for easy deployment.

## Project Structure

```text
freshproxy/
├── freshproxy/
│   ├── __init__.py      # Makes 'freshproxy' a package
│   ├── app.py           # Application factory & CORS setup
│   ├── config.py        # Environment variables, whitelists
│   └── proxy_routes.py  # Blueprint with the '/' GET route
├── tests/
│   ├── test_config.py   # Example environment var tests
│   └── test_proxy.py    # Proxy route tests (mocking requests)
├── requirements.txt     # Dependencies (Flask, requests, etc.)
├── pyproject.toml       # Project metadata & optional deps
├── run.py               # Dev entry point
├── Dockerfile           # Container-based deployment
├── .env.example         # Example environment variables (no secrets)
├── .gitignore
└── README.md
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/hstct/FreshProxy.git
cd FreshProxy
```
2. Install dependencies (pick one approach):
    - Using **pip** `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    - Using **pip** with `pyproject.toml`:
    ```bash
    pip install .
    # or for dev/test extras
    pip install .[test,lint]
    ```

## Configuration

1. Create a `.env` file:
```bash
cp .env.example .env
```
2. Edit the `.env` file with your configurations:
```dotenv
FRESHRSS_API_TOKEN=your-secret-token
FRESHRSS_BASE_URL=https://freshrss.example.com/greader.php

FRESHPROXY_ALLOWED_ORIGINS=http://localhost:3000,https://mydomain.com
FRESHPROXY_HOST=0.0.0.0
FRESHPROXY_PORT=8000
FRESHPROXY_DEBUG=False
FRESHPROXY_REQUEST_TIMEOUT=10
```


### Environment Variables

- `FRESHRSS_API_TOKEN`: Secret token used to authenticate with your FreshRSS instance.
- `FRESHRSS_BASE_URL`: Root URL of your FreshRSS GReader API (no trailing slash).
- `FRESHPROXY_ALLOWED_ORIGINS`: Comma-separated list of origins for CORS.
- `FRESHPROXY_HOST`: The Flask host. (Default: `0.0.0.0`)
- `FRESHPROXY_PORT`: The Flask port. (Default: `8000`)
- `FRESHPROXY_DEBUG`: Enable debug mode. (Default: `False`)
- `FRESHPROXY_REQUEST_TIMEOUT`: Timeout for proxied requests in seconds. (Default: `10`)

## Running the Proxy

### Local Development

1. Ensure `.env` is configured with your secrets and config.
2. Run the application:
```bash
python run.py
```
3. Check the endpoint:
```bash
curl "https://localhost:8000/subscriptions"
```
or open in your browser.

### Production

**Gunicorn** is recommended for the application in production:

```bash
gunicorn --bind 0.0.0.0:8000 freshproxy.app:create_app --worker-class sync --workers 4
```

## Docker Usage

A Dockerfile is included for container-based deployment:

1. Build the Docker image:
```bash
docker build -t freshproxy .
```
2. Run the container:
```bash
docker run -p 8000:8000 \
  -e FRESHRSS_API_TOKEN="my-secret-token" \
  -e FRESHRSS_BASE_URL="https://freshrss.example.com/greader.php" \
  -e FRESHPROXY_ALLOWED_ORIGINS="http://localhost:3000,https://mydomain.com" \
  -e FRESHPROXY_HOST="0.0.0.0" \
  -e FRESHPROXY_PORT=8000 \
  -e FRESHPROXY_DEBUG=False \
  -e FRESHPROXY_REQUEST_TIMEOUT=10 \
  freshproxy
```
3. Test:
```bash
curl "http://localhost:8000/subscriptions"
```

## Contributing

Contributions via pull requests or suggestions in issues are welcome! Please open an issue for discussion first if it's a major change. When contributing:

1. Fork & clone the repository locally.
2. Create new feature/bug branch: `git checkout -b feature/my-feature`.
3. Make changes, add tests if relevant.
4. Lint & format your code:
```bash
black .
flake8 .
```
5. Commit & push your branch, then open a pull request.
