from flask import Flask

from ratings.routes import ratings_bp
from suggestion.routes import suggestion_bp
import config

# cria uma instância do Flask
app = Flask(__name__)

# registra o blueprint das rotas
app.register_blueprint(ratings_bp)
app.register_blueprint(suggestion_bp)

# função principal para iniciar o servidor
if __name__ == "__main__":
    app.run(debug=config.FLASK_DEBUG)