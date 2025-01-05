# Stage 1: Builder
FROM python:3.10-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc
COPY requirements.txt .

RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.10-slim
WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY . /app
ENV PATH=/root/.local/bin:$PATH

RUN useradd -m appuser
USER appuser

# Expose the port Flast/gunicorn will run on
EXPOSE 8000

# For production, run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "freshproxy.app:create_app", "--worker-class", "sync", "--workers", "4"]
