from flask import Flask

from movies.routes import movies_bp

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.register_blueprint(movies_bp)

# main app initialization

if __name__ == "__main__":

    # app.run(debug=True)
    app.run()