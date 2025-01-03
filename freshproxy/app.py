import logging

from flask import Flask
from flask_cors import CORS

from freshproxy.config import ALLOWED_ORIGINS, DEBUG
from freshproxy.proxy_routes import proxy_bp


def create_app():
    """
    Application factory that creates and configures the Flask app.
    """
    app = Flask(__name__)

    logging.basicConfig(level=logging.INFO if not DEBUG else logging.DEBUG)

    app.register_blueprint(proxy_bp, url_prefix="")

    CORS(app, resources={r"/": {"origins": ALLOWED_ORIGINS}})

    return app
