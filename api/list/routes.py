from flask import Blueprint

from list.controller import delete_listed_movie, get_listed_movies, list_movie

list_bp = Blueprint("list", __name__)

@list_bp.route("/listed-movies", methods=["GET"])
def retrieve_listed_items():
    return get_listed_movies()

@list_bp.route("/sync-movie/<tconst>", methods=["POST"])
def sync_movie_item(tconst):
    return list_movie(tconst)

@list_bp.route("/sync-movie/<tconst>", methods=["DELETE"])
def remove_listed_movie_item(tconst):
    return delete_listed_movie(tconst)