from flask import (
    Blueprint,
    jsonify,
    request
)

from config import get_mongo_collection
from generate_review.controller import (
    create_and_save_movie_review,
    get_movie_review
)

generate_review_bp = Blueprint("generate_review", __name__)


# Cria e salva a resenha e o enredo para um filme favoritado
@generate_review_bp.route("/favorited-movies/<tconst>/review", methods=["POST"])
def create_review_and_plot(tconst):
    result = create_and_save_movie_review(tconst)
    
    if result["status"] == 200:
        return jsonify({"message": result["message"]}), 200
    elif result["status"] == 404:
        return jsonify({"message": result["message"]}), 404
    else:
        return jsonify({"message": result["message"]}), 500


# Recupera a resenha e o enredo de um filme favoritado
@generate_review_bp.route("/favorited-movies/<tconst>/review", methods=["GET"])
def get_review_and_plot(tconst):
    result = get_movie_review(tconst)

    if result["status"] == 200:
        return jsonify({"data": result["data"]}), 200
    elif result["status"] == 404:
        return jsonify({"message": result["message"]}), 404
    else:
        return jsonify({"message": result["message"]}), 500