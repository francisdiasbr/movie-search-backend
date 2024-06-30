from flask import Blueprint, jsonify, request

from principals.controller import (
  principals_retrieve,
  principals_search
)

principals_bp = Blueprint("principals", __name__)

@principals_bp.route("/principals/<item_id>", methods=["GET"])
def get_principals(item_id):

    result = principals_retrieve(item_id)

    return jsonify(result)

@principals_bp.route("/principals/search", methods=["POST"])
def post_principals_search():

    request_data = request.get_json()

    principals_array = principals_search(
        filters=request_data["filters"],
        sorters=request_data.get("sorters", ["name", 1]),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
    )

    return jsonify(principals_array)