from flask import Blueprint, jsonify, request

from favorites.controller import delete_favorited_movie, edit_favorited_movie, get_favorited_movies, favorite_movie, get_favorited_movie

favorites_bp = Blueprint("favorites", __name__)

#filtra os filmes favoritados
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


# favorita um filme (e obtém dados do filme)
@favorites_bp.route("/movie/<tconst>", methods=["POST"])
def sync_movie_item(tconst):
    return favorite_movie(tconst)

@favorites_bp.route("/movie/<tconst>/edit", methods=["PUT"])
def update_favorited_movie_item(tconst):
    request_data = request.get_json()
    print('edit request data', request_data)
    primaryTitle = request_data.get('primaryTitle'),
    startYear = request_data.get('startYear')
    soundtrack = request_data.get('soundtrack')
    wiki = request_data.get('wiki')
    
    return edit_favorited_movie(tconst, primaryTitle, startYear, soundtrack, wiki)


@favorites_bp.route("/movie/<tconst>", methods=["DELETE"])
def remove_favorited_movie_item(tconst):
    return delete_favorited_movie(tconst)



@favorites_bp.route("/movie/<tconst>", methods=["GET"])
def get_favorited_movie_item(tconst):
    return get_favorited_movie(tconst)