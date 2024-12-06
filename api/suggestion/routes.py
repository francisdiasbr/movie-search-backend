from flask import Blueprint

from suggestion.controller import search_movie_suggestion

suggestion_bp = Blueprint("suggestion", __name__)


@suggestion_bp.route("/suggestion", methods=["GET"])
def get_suggestions():
    return search_movie_suggestion()
