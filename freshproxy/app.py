import logging

from flask import Flask
from flask_cors import CORS
from freshproxy.config import ALLOWED_ORIGINS
from freshproxy.proxy_routes import proxy_bp


def create_app():
    """
    Application factory that creates and configures the Flask app.
    """
    app = Flask(__name__)

    logging.basicConfig(level=logging.INFO)

    CORS(app, resources={r"/": {"origins": ALLOWED_ORIGINS}})

    app.register_blueprint(proxy_bp, url_prefix="")

    return app
