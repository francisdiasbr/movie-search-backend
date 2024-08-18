from flask import Blueprint, jsonify, request

from list.controller import delete_listed_movie, get_listed_movies, list_movie

list_bp = Blueprint("list", __name__)

@list_bp.route("/listed-movies/search", methods=["POST"])
def retrieve_listed_items():
    request_data = request.get_json()

    search_array = get_listed_movies(
        filters=request_data.get("filters", {}),
        sorters=request_data.get("sorters", ["_id", -1]),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
    )

    return search_array

@list_bp.route("/sync-movie/<tconst>", methods=["POST"])
def sync_movie_item(tconst):
    return list_movie(tconst)

@list_bp.route("/sync-movie/<tconst>", methods=["DELETE"])
def remove_listed_movie_item(tconst):
    return delete_listed_movie(tconst)