import logging

from flask import Flask
from flask_cors import CORS

from freshproxy.config import ALLOWED_ORIGINS, LOG_FORMAT, LOG_LEVEL
from freshproxy.proxy_routes import proxy_bp


def create_app() -> Flask:
    """
    Application factory that creates and configures the Flask app.

    Returns:
        Flask: Configured Flask application instance.
    """
    app = Flask(__name__)

    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)
    logger.debug("Logging is configured")

    app.register_blueprint(proxy_bp)
    logger.debug("Blueprint 'proxy_bp' registered.")

    CORS(app, resources={r"/": {"origins": ALLOWED_ORIGINS}})

    return app
