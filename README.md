# FreshProxy

A **Flask**-based proxy for [FreshRSS](https://github.com/FreshRSS/FreshRSS) that fetches feed data securely, whitelists specific API endpoints, and controls CORS. Configurable via environment variables (or a `.env` file).

## Overview

**FreshProxy** is designed to act as a small, focused **HTTP proxy** in front of a **FreshRSS** instance. It hides your auth token from client applications by forwarding authorized requests, only exposing safe, **whitelisted** sub-endpoints. This helps prevent SSRF attacks or direct credential leaks.

## Features

- **Whitelist** approach for `endpoint` subpaths (like `subscription/list`, etc).
- **CORS** restrictions to only allow certain origins.
- **Timeout** and error handling for upstream requests.
- **Environment-based configuration** (via `.env` or standard env vars).

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

1. **Clone** the repository:
```bash
git clone https://github.com/hstct/FreshProxy.git
cd FreshProxy
```
2. **Install dependencies** (pick one approach):
    - Using **requirements.txt**: `pip install -r requirements.txt`
    - Using **pyproject.toml**:
    ```bash
    pip install .
    # or for dev/test extras
    pip install .[test,lint]
    ```
3. **(Optional) Provide a `.env` file**:
    - Copy `.env.example` to `.env`.
    - Fill in actual secrets and config.
    - See [Configuration via .env](#configuration-via-env) below.

## Configuration via .env

**freshproxy/config.py** uses `python-dotenv` to load environment variables.

- `FRESHRSS_API_TOKEN`: Secret token used to call FreshRSS behind the scenes.
- `FRESHRSS_BASE_URL`: Root URL of your FreshRSS GReader API (no trailing slash).
- `FRESHPROXY_ALLOWED_ENDPOINTS`: Comma-separated subpaths that the proxy allows (e.g. `subscription/list,stream/contents`).
- `FRESHPROXY_ALLOWED_PREFIXES`: Comma-separated prefixes for endpoints that allow subpaths.
- `FRESHPROXY_ALLOWED_ORIGINS`: Comma-separated list of origins for CORS.
- `FRESHPROXY_HOST`: The Flask host. (Default: `0.0.0.0`)
- `FRESHPROXY_PORT`: The Flask port. (Default: `8000`)
- `FRESHPROXY_DEBUG`: Whether or not to run the application in Debug mode. (Default: `False`)o

A sample `.env.example` might look like:

```dotenv
FRESHRSS_API_TOKEN=your-secret-token
FRESHRSS_BASE_URL=https://freshrss.example.com/greader.php

FRESHPROXY_ALLOWED_ENDPOINTS=subscription/list,stream/contents,marker/tag/lists
FRESHPROXY_ALLOWED_PREFIXES=stream/contents/feed/
FRESHPROXY_ALLOWED_ORIGINS=http://localhost:3000,https://mydomain.com
FRESHPROXY_HOST=0.0.0.0
FRESHPROXY_PORT=8000
FRESHPROXY_DEBUG=False
```

## Running the Proxy

### Local Development

1. Edit or create `.env` with your secrets and config.
2. Run in dev mode:
```bash
python run.py
```
3. Check the endpoint:
```bash
curl "https://localhost:8000/?endpoint=subscription/list"
```
or open in your browser.

### Production

**Gunicorn** is recommended:
```bash
gunicorn --bind 0.0.0.0:8000 freshproxy.app:create_app()
```

Ensure you set env variables (e.g., via Docker, a systemd file, or your hosting environment).

## Docker Usage

A **Dockerfile** is included for container-based deployment:

1. Build the Docker image:
```bash
docker build -t freshproxy .
```
2. Run it:
```bash
docker run -p 8000:8000 \
  -e FRESHRSS_API_TOKEN="my-secret-token" \
  -e FRESHRSS_BASE_URL="https://freshrss.example.com/greader.php" \
  -e FRESHPROXY_ALLOWED_ENDPOINTS="subcription/list" \
  -e FRESHPROXY_ALLOWED_PREFIXES="stream/contents" \
  -e FRESHPROXY_ALLOWED_ORIGINS="http://localhost:3000,https://mydomain.com" \
  -e FRESHPROXY_HOST="0.0.0.0" \
  -e FRESHPROXY_PORT=8000 \
  -e FRESHPROXY_DEBUG=False \
  freshproxy
```
3. Test:
```bash
curl "http://localhost:8000/?endpoint=subscription/list"
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

We appreciate your help in making **FreshProxy** more robust and easier to use!
