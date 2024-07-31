from flask import Blueprint

from sync.controller import get_synced_items, movie_sync

sync_bp = Blueprint("sync", __name__)

@sync_bp.route("/sync/<tconst>", methods=["POST"])
def sync(tconst):
    return movie_sync(tconst)

@sync_bp.route("/sync", methods=["GET"])
def synced_items():
    return get_synced_items()