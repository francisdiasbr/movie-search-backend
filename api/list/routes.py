from flask import Blueprint, jsonify, request

from list.controller import delete_listed_movie, edit_listed_movie, get_listed_movies, list_movie

list_bp = Blueprint("list", __name__)

#filtra os filmes listados
@list_bp.route("/listed-movies/search", methods=["POST"])
def retrieve_listed_items():
    #captura os dados enviados na requisição
    request_data = request.get_json()
    # print('request_data', request_data)

    search_array = get_listed_movies(
        filters=request_data.get("filters", {}),
        sorters=request_data.get("sorters", ["_id", -1]),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
    )

    # print('search_array', search_array)
    return search_array

# favorita um filme (e obtém dados do filme)
@list_bp.route("/sync-movie/<tconst>", methods=["POST"])
def sync_movie_item(tconst):
    return list_movie(tconst)

@list_bp.route("/sync-movie/<tconst>/edit", methods=["PUT"])
def update_listed_movie_item(tconst):
    request_data = request.get_json()
    # print('edit request data', request_data)
    primaryTitle = request_data.get('primaryTitle'),
    startYear = request_data.get('startYear')
    soundtrack = request_data.get('soundtrack')
    wiki = request_data.get('wiki')
    
    return edit_listed_movie(tconst, primaryTitle, startYear, soundtrack, wiki)


@list_bp.route("/sync-movie/<tconst>", methods=["DELETE"])
def remove_listed_movie_item(tconst):
    return delete_listed_movie(tconst)