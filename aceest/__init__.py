"""ACEest Fitness & Gym - Flask application package."""
import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

__version__ = "1.0.0"


def create_app(test_config=None):
    """Application factory.

    ``test_config`` overrides the default configuration, which lets the test
    suite point the app at a throwaway database.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "ACEEST_DB", os.path.join(app.instance_path, "aceest_fitness.db")
        ),
    )
    if test_config:
        app.config.update(test_config)

    db_dir = os.path.dirname(app.config["DATABASE"])
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    @app.get("/")
    def index():
        return jsonify(
            service="ACEest Fitness & Gym API",
            version=__version__,
            endpoints=sorted(
                str(rule) for rule in app.url_map.iter_rules()
                if rule.endpoint != "static"
            ),
        )

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=__version__)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        """Return JSON instead of HTML for every HTTP error."""
        return jsonify(error=err.name, message=err.description), err.code

    return app
