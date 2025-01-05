# Stage 1: Builder
FROM python:3.10-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.10-slim
WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY . /app
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONUNBUFFERED=1

RUN useradd -m appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose the port Flast/gunicorn will run on
EXPOSE 8000

# For production, run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "freshproxy.wsgi:app", "--worker-class", "sync", "--workers", "4"]
