from flask import (
    Blueprint,
    jsonify,
    request
)

from favorites.controller import (
    delete_favorited_movie,
    edit_favorited_movie,
    favorite_movie,
    get_favorited_movie,
    get_favorited_movies
)

favorites_bp = Blueprint("favorites", __name__)


# favorita um filme
@favorites_bp.route("/movie/<tconst>", methods=["POST"])
def sync_movie_item(tconst):
    return favorite_movie(tconst)


# recupera um filme favoritado
@favorites_bp.route("/movie/<tconst>", methods=["GET"])
def get_favorited_movie_item(tconst):
    return get_favorited_movie(tconst)


# edita um filme
@favorites_bp.route("/movie/<tconst>", methods=["PUT"])
def update_favorited_movie_item(tconst):
    request_data = request.get_json()
    # print('edit request data', request_data)
    originalTitle = request_data.get('originalTitle')
    startYear = request_data.get('startYear')
    soundtrack = request_data.get('soundtrack')
    wiki = request_data.get('wiki')
    
    return edit_favorited_movie(tconst, originalTitle, startYear, soundtrack, wiki)


# remove um filme
@favorites_bp.route("/movie/<tconst>", methods=["DELETE"])
def remove_favorited_movie_item(tconst):
    return delete_favorited_movie(tconst)


# filtra os filmes favoritados por termo de busca
@favorites_bp.route("/favorited-movies/search", methods=["POST"])
def retrieve_favorited_items():
    request_data = request.get_json()
    if not isinstance(request_data, dict):
        return jsonify({"status": 400, "message": "Invalid input data"}), 400
    search_array = get_favorited_movies(
        filters=request_data.get("filters", {}),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
        search_term = request_data.get("search_term", "")
    )
    return search_array