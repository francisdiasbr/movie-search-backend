from flask import Blueprint

from sync.controller import get_synced_items, movie_sync

sync_bp = Blueprint("sync", __name__)

@sync_bp.route("/sync", methods=["POST"])
def sync():
    return movie_sync()

@sync_bp.route("/sync", methods=["GET"])
def synced_items():
    return get_synced_items()