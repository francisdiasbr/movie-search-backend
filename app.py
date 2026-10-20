import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_restx import Api

# Without this the root level stays at WARNING and every logger.info is dropped.
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from config import DatabaseUnavailable
from main_images.controller import StorageUnavailable
from favorites.scrapper import IMDBUnavailable
from belas_artes.routes import belas_artes_bp
from favorites.routes import favorites_bp
from keywords.routes import keywords_bp
from main_images.routes import main_images_bp
from write_review.routes import write_review_bp

# Flask instance
app = Flask(__name__)
app.url_map.strict_slashes = False

# CORS config
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
            "allow_headers": [
                "Content-Type",
                "Authorization",
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Headers",
                "Access-Control-Allow-Methods",
            ],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
        }
    },
)

# Swagger config
api = Api(
    app,
    version="1.0",
    title="Movies API",
    description="API para gerenciamento de filmes",
    doc="/docs",
    prefix="/api",
    default_mediatype="application/json",
    default="Movies API",
    default_label="Endpoints disponíveis",
    validate=True,
    ordered=True,
    catch_all_404s=True,
    serve_challenge_on_401=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
)


@api.errorhandler(DatabaseUnavailable)
def handle_database_unavailable(error):
    """Every controller reaches Mongo through get_mongo_collection, so this is
    the single place that answers when the database is down."""
    return {"message": str(error)}, 503


@api.errorhandler(StorageUnavailable)
def handle_storage_unavailable(error):
    return {"message": str(error)}, 503


@api.errorhandler(IMDBUnavailable)
def handle_imdb_unavailable(error):
    """The scraper raises this when the AWS WAF blocks every attempt; the fix
    is renewing the session (./verify_imdb.sh), not a different tconst."""
    return {"message": str(error)}, 503


# Root route
@app.route("/")
def home():
    return jsonify(
        {
            "status": "online",
            "message": "Movie Search API is running",
            "docs": "/docs",
            "version": "1.0",
        }
    )


# Route to list all routes
@app.route("/routes")
def list_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(
            {
                "endpoint": rule.endpoint,
                "methods": list(rule.methods),
                "path": str(rule),
            }
        )
    return jsonify(routes)


# register blueprints
app.register_blueprint(favorites_bp)
app.register_blueprint(keywords_bp)
app.register_blueprint(main_images_bp)
app.register_blueprint(write_review_bp)
app.register_blueprint(belas_artes_bp)

# Add namespaces
api.add_namespace(favorites_bp.api)
api.add_namespace(keywords_bp.api)
api.add_namespace(main_images_bp.api)
api.add_namespace(write_review_bp.api)
api.add_namespace(belas_artes_bp.api)

# main function to start the server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
