from flask import Blueprint, jsonify, request

from ratings.controller import (
  movie_with_rating_retrieve,
  ratings_retrieve,
  ratings_search
)

ratings_bp = Blueprint("ratings", __name__)

# Pesquisa as avaliações de um tconst
@ratings_bp.route("/ratings/<tconst>", methods=["GET"])
def get_ratings(tconst):
    result = ratings_retrieve(tconst)
    return jsonify(result)

# Pesquisa as avaliações de um tconst
@ratings_bp.route("/ratings/search", methods=["POST"])
def post_ratings_search():
    request_data = request.get_json()
    ratings_array = ratings_search(
        filters=request_data["filters"],
        sorters=request_data.get("sorters", ["name", 1]),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
    )
    return jsonify(ratings_array)

# Pesquisa um filme com avaliação
@ratings_bp.route("/movie-with-rating/<tconst>", methods=["GET"])
def get_movie_with_rating(tconst):
    result = movie_with_rating_retrieve(tconst)
    return jsonify(result)