import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, Namespace

import config
from favorites.routes import favorites_bp
from directors.routes import directors_bp
from generate_blogpost.routes import generate_blogpost_bp
from keywords.routes import keywords_bp
from movies.routes import movies_bp
from write_review.routes import write_review_bp
from personal_opinion.routes import personal_opinion_bp
from generate_blogpost_trivia.routes import generate_blogpost_trivia_bp
from images.routes import images_bp

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
            "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Origin",
                            "Access-Control-Allow-Headers", "Access-Control-Allow-Methods"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
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
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"]
)

# Root route
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Movie Search API is running",
        "docs": "/docs",
        "version": "1.0"
    })

# Route to list all routes
@app.route('/routes')
def list_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "path": str(rule)
        })
    return jsonify(routes)

# register blueprints
app.register_blueprint(directors_bp)
app.register_blueprint(favorites_bp)
app.register_blueprint(generate_blogpost_bp)
app.register_blueprint(keywords_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(write_review_bp)
app.register_blueprint(personal_opinion_bp)
app.register_blueprint(generate_blogpost_trivia_bp)
app.register_blueprint(images_bp)

# Add namespaces
api.add_namespace(directors_bp.api)
api.add_namespace(favorites_bp.api)
api.add_namespace(keywords_bp.api)
api.add_namespace(generate_blogpost_bp.api)
api.add_namespace(movies_bp.api)
api.add_namespace(write_review_bp.api)
api.add_namespace(personal_opinion_bp.api)
api.add_namespace(generate_blogpost_trivia_bp.api)
api.add_namespace(images_bp.api)

# main function to start the server
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=False)
