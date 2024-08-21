from flask import Blueprint, jsonify, request

from movies.controller import get_movies

movies_bp = Blueprint("movies", __name__)

@movies_bp.route("/movies/search", methods=["POST"])
def retrieve_items():
    request_data = request.get_json()

    search_array = get_movies(
        filters=request_data.get("filters", {}),
        sorters=request_data.get("sorters", ["_id", -1]),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
        search_term = request_data.get("search_term", "")
    )

    return search_array
