from flask import Flask
from flask_cors import CORS
from flask_restx import Api

import config
from favorites.routes import favorites_bp
from generate_review.routes import generate_review_bp
from movies.routes import movies_bp
from ratings.routes import ratings_bp
from suggestion.routes import suggestion_bp
from write_review.routes import write_review_bp

# cria uma instância do Flask
app = Flask(__name__)
CORS(app)

# Configuração do Swagger
api = Api(
    app,
    version='1.0',
    title='Movies API',
    description='API para gerenciamento de filmes',
    doc='/docs'  # A documentação estará disponível em /docs
)

# registra o blueprint das rotas
app.register_blueprint(favorites_bp)
app.register_blueprint(generate_review_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(ratings_bp)
app.register_blueprint(suggestion_bp)
app.register_blueprint(write_review_bp)

# Adiciona o namespace de filmes
api.add_namespace(movies_bp.api)
api.add_namespace(favorites_bp.api)

# função principal para iniciar o servidor
if __name__ == "__main__":
    app.run(debug=config.FLASK_DEBUG, host='0.0.0.0', port=5001)