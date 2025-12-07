import os

from dynaconf import settings
from flask import Flask


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = settings.SECRET_KEY or os.urandom(24)

    if test_config:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    from bookmarks.routes import bp

    app.register_blueprint(bp)

    return app
