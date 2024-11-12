from flask import Blueprint, jsonify, request

from movies.controller import get_movies

movies_bp = Blueprint("movies", __name__)

# Pesquisa os filmes da base de dados
@movies_bp.route("/movies/search", methods=["POST"])
def retrieve_items():
    request_data = request.get_json()

    search_array = get_movies(
        filters=request_data.get("filters", {}),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
        search_term = request_data.get("search_term", ""),
        sorters=request_data.get("sorters", [("_id", -1)])
    )

    return search_array
