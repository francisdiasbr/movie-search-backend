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

# cria uma instância do Flask
app = Flask(__name__)
app.url_map.strict_slashes = False

# Configuração do CORS
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    },
)

# Configuração do Swagger
api = Api(
    app,
    version="1.0",
    title="Movies API",
    description="API para gerenciamento de filmes",
    doc="/docs",
    prefix="/api"  # Adiciona prefixo para todas as rotas da API
)

# Rota raiz simples
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Movie Search API is running",
        "docs": "/docs",
        "version": "1.0"
    })

# Rota para listar todas as rotas
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

# registra o blueprint das rotas
app.register_blueprint(directors_bp)
app.register_blueprint(favorites_bp)
app.register_blueprint(generate_blogpost_bp)
app.register_blueprint(keywords_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(write_review_bp)
app.register_blueprint(personal_opinion_bp)
app.register_blueprint(generate_blogpost_trivia_bp)


# Adiciona os namespaces
api.add_namespace(directors_bp.api)
api.add_namespace(favorites_bp.api)
api.add_namespace(keywords_bp.api)
api.add_namespace(generate_blogpost_bp.api)
api.add_namespace(movies_bp.api)
api.add_namespace(write_review_bp.api)
api.add_namespace(personal_opinion_bp.api)
api.add_namespace(generate_blogpost_trivia_bp.api)


# função principal para iniciar o servidor
if __name__ == "__main__":
    # Heroku fornece a porta via variável de ambiente PORT
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
