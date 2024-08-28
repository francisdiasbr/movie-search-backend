from flask import Blueprint

from details.controller import get_details_movie

details_bp = Blueprint("details", __name__)

@details_bp.route("/favorited-movies/details", methods=["GET"])
def retrieve_details_item():
    return get_details_movie()