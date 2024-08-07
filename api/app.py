from flask import Flask

import config
from ratings.routes import ratings_bp
from suggestion.routes import suggestion_bp
from sync.routes import sync_bp

# cria uma instância do Flask
app = Flask(__name__)

# registra o blueprint das rotas
app.register_blueprint(ratings_bp)
app.register_blueprint(suggestion_bp)
app.register_blueprint(sync_bp)

# função principal para iniciar o servidor
if __name__ == "__main__":
    app.run(debug=config.FLASK_DEBUG)