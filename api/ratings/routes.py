from flask import Blueprint, jsonify, request

from ratings.controller import (
  movie_with_rating_retrieve,
  ratings_retrieve,
  ratings_search
)

ratings_bp = Blueprint("ratings", __name__)

@ratings_bp.route("/ratings/<item_id>", methods=["GET"])
def get_ratings(item_id):
    result = ratings_retrieve(item_id)
    return jsonify(result)

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

@ratings_bp.route("/movie-with-rating/<item_id>", methods=["GET"])
def get_movie_with_rating(item_id):
    result = movie_with_rating_retrieve(item_id)
    return jsonify(result)