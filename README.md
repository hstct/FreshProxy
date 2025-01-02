# FreshProxy

A minimal **Flask**-based proxy for forwarding requests to a **FreshRSS** Greader API endpoint. This proxy handles **authorization**, whitelists specific sub-endpoints, and returns JSON data to your front end (or other clients) with optional CORS restrictions.

---

## Overview

**FreshProxy** is designed for situations where you want to:
- Keep a **FreshRSS** feed aggregator **private** behind a token.
- Provide a **simple** proxy endpoint to your front-end or public apps without exposing credentials.
- Restrict which API endpoints can be called (to prevent SSRF or malicious usage).
- Control **CORS** so only certain origins can call the proxy.

**Key features:**
- **Whitelist** approach for valid sub-endpoints (e.g., `subscription/list`, `stream/contents`).
- **Environment-based** auth token and base URL (so you don't commit secrets).
- **Timeout** and error handling (return 504 on timeouts, 502 on request errors, etc).

---

## Project Structure

```bash
.
├── freshproxy
│   ├── __init__.py      # Makes 'freshproxy' a package
│   ├── app.py           # Application factory & CORS setup
│   ├── config.py        # Environment variables, whitelists
│   └── proxy_routes.py  # Blueprint with the '/' GET route
├── tests
│   ├── test_config.py   # Example environment var tests
│   └── test_proxy.py    # Proxy route tests (mocking requests)
├── requirements.txt     # Dependencies (Flask, requests, etc.)
├── pyproject.toml       # Project metadata & optional deps
├── run.py               # Dev entry point
├── Dockerfile           # Container-based deployment
├── .gitignore
└── README.md            # This file
```

---

## Installation

1. **Clone** the repo: `git clone https://github.com/hstct/FreshProxy.git`
2. **Install dependencies** (pick one approach):
    - Using **requirements.txt**: `pip install -r requirements.txt`
    - Using **pyproject.toml**:
    ```bash
    pip install .
    # or for dev/test extras
    pip install .[test,lint]
    ```
3. **Set environment variables** (at least):
```bash
export FRESHRSS_API_TOKEN="my-secret-token"
export FRESHRSS_BASE_URL="https://freshrss.example.com/greader.php"
```

---

## Configuration

- `FRESHRSS_API_TOKEN`: The auth token used by FreshRSS to authenticate requests.
- `FRESHRSS_BASE_URL`: The base URL of your FreshRSS GReader API endpoint (no trailing slash).

In `freshproxy/config.py`:

- `ALLOWED_ENDPOINTS`: A set of valid suppaths. Any request with an `endpoint` not in this list returns 403.
- `ALLOWED_ORIGINS`: Restrict which domains can call your proxy (CORS).

---

## Running the App

### Development Mode

1. **Local**:
```bash
python run.py
```
This starts Flask on `http://0.0.0.0:8000`. By default, `debug=False`; adjust as needed.

2. **Check**:
```bash
curl "http://localhost:8000/?endpoint=subscription/list"
```
or open in your browser.

### Production

1. **gunicorn** (common WSGI server):
```bash
gunicorn --bind 0.0.0.0:8000 freshproxy.app:create_app()
```

2. **Configuration**:
    - You should still set environment variables for tokens and base URL.
    - Make sure to restrict or manage logs, timeouts, etc. in production environment.

---

## Docker Usage

A **Dockerfile** is included for container-based deployment:

1. **Build** the Docker image:
```bash
docker build -t freshproxy .
```

2. **Run**:
```bash
docker run -p 8000:8000 \
  -e FRESHRSS_API_TOKEN="my-secret-token" \
  -e FRESHRSS_BASE_URL="https://freshrss.example.com/greader.php" \
  freshproxy
```

3. **Access**:
```bash
curl "http://localhost:8000/?endpoint=subscription/list"
```

---

## Contributing

Contributions via pull requests or suggestions in issues are welcome. When contributing:

1. **Fork** & **clone** the repo.
2. Create new feature/bug branch: `git checkout -b feature/my-feature`.
3. Make changes, add tests if needed.
4. **Lint** & **format** your code:
```bash
black .
flake8 .
```
5. **Commit** & **push** your branch, then open a PR.

We appreciate your help in making **FreshProxy** more robust and easier to use!
