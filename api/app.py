from flask import Flask
from flask_cors import CORS

import config
from details.routes import details_bp
from ratings.routes import ratings_bp
from suggestion.routes import suggestion_bp
from list.routes import list_bp
from movies.routes import movies_bp

# cria uma instância do Flask
app = Flask(__name__)
CORS(app)

# registra o blueprint das rotas
app.register_blueprint(details_bp)
app.register_blueprint(list_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(ratings_bp)
app.register_blueprint(suggestion_bp)

# função principal para iniciar o servidor
if __name__ == "__main__":
    app.run(debug=config.FLASK_DEBUG, port=5000)