from flask import Flask

from movies.routes import movies_bp
from ratings.routes import ratings_bp
from crew.routes import crew_bp
from principals.routes import principals_bp
from suggestion.routes import moviesuggestion_bp

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.register_blueprint(movies_bp)
app.register_blueprint(ratings_bp)
app.register_blueprint(crew_bp)
app.register_blueprint(principals_bp)
app.register_blueprint(moviesuggestion_bp)

# main app initialization

if __name__ == "__main__":

    # app.run(debug=True)
    app.run()