from flask import (
    Blueprint,
    jsonify,
    request
)

from generate_review.controller import (
    create_and_save_movie_review,
    get_movie_review,
    get_generated_reviews
)

generate_review_bp = Blueprint("generate_review", __name__)


# Cria e salva a resenha e o enredo para um filme favoritado
@generate_review_bp.route("/favorited-movies/<tconst>/generate-review", methods=["POST"])
def create_review_and_plot(tconst):
    return create_and_save_movie_review(tconst)


# Recupera a resenha e o enredo de um filme favoritado
@generate_review_bp.route("/favorited-movies/<tconst>/generate-review", methods=["GET"])
def get_review_and_plot(tconst):
    return get_movie_review(tconst)


# Recupera as resenhas e enredos gerados
@generate_review_bp.route("/favorited-movies/generate-review/search", methods=["POST"])
def retrieve_generated_reviews():
    request_data = request.get_json()
    if not isinstance(request_data, dict):
        return jsonify({"status": 400, "message": "Invalid input data"}), 400
    search_array = get_generated_reviews(
        filters=request_data.get("filters", {}),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
    )
    return search_array