from flask import Blueprint, jsonify, request

from movies.controller import (
    movies_create,
    movies_delete,
    movies_retrieve,
    movies_search,
    movies_update,
)

movies_bp = Blueprint("movies", __name__)


@movies_bp.route("/movies", methods=["POST"])
def post_movies_create():

    request_data = request.get_json()

    result = movies_create(request_data)

    return jsonify(result)


@movies_bp.route("/movies/<item_id>", methods=["GET"])
def get_movies(item_id):

    result = movies_retrieve(item_id)

    return jsonify(result)


@movies_bp.route("/movies/<item_id>", methods=["DELETE"])
def delete_movies(item_id):

    result = movies_delete(item_id)

    return jsonify(result)


@movies_bp.route("/movies/search", methods=["POST"])
def post_movies_search():

    request_data = request.get_json()

    print("Request data movies search:", request_data)

    movies_array = movies_search(
        filters=request_data["filters"],
        sorters=request_data.get("sorters", ["name", 1]),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
    )

    return jsonify(movies_array)


@movies_bp.route("/movies/<item_id>", methods=["PUT"])
def put_movies_update(item_id):

    request_data = request.get_json()

    result = movies_update(item_id, request_data)

    return jsonify(result)


