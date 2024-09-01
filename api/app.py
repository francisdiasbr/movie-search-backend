from flask import Flask
from flask_cors import CORS

import config
from favorites.routes import favorites_bp
from generate_review.routes import generate_review_bp
from movies.routes import movies_bp
from ratings.routes import ratings_bp
from suggestion.routes import suggestion_bp

# cria uma instância do Flask
app = Flask(__name__)
CORS(app)

# registra o blueprint das rotas
app.register_blueprint(favorites_bp)
app.register_blueprint(generate_review_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(ratings_bp)
app.register_blueprint(suggestion_bp)

# função principal para iniciar o servidor
if __name__ == "__main__":
    app.run(debug=config.FLASK_DEBUG, port=5000)