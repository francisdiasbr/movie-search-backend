from flask import Blueprint

from sync.controller import delete_synced_movie, get_synced_movies, movie_sync

sync_bp = Blueprint("sync", __name__)

@sync_bp.route("/sync", methods=["GET"])
def synced_items():
    return get_synced_movies()

@sync_bp.route("/sync/<tconst>", methods=["POST"])
def sync_item(tconst):
    return movie_sync(tconst)

@sync_bp.route("/sync/<tconst>", methods=["DELETE"])
def delete_sync(tconst):
    return delete_synced_movie(tconst)