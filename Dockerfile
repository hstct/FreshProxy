FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Optionally set environment variables here or at runtime
# ENV FRESHRSS_API_TOKEN=some-token
# ENV FRESHRSS_BASE_URL=https://your-freshrss-instance

# Expose the port Flast/gunicorn will run on
EXPOSE 8000

# For production, run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "frsshproxy.app:create_app()"]
