from flask import Blueprint, jsonify, request

from crew.controller import (
  crew_retrieve,
  crew_search
)

crew_bp = Blueprint("crew", __name__)

@crew_bp.route("/crew/<item_id>", methods=["GET"])
def get_crew(item_id):

    result = crew_retrieve(item_id)

    return jsonify(result)

@crew_bp.route("/crew/search", methods=["POST"])
def post_crew_search():

    request_data = request.get_json()

    crew_array = crew_search(
        filters=request_data["filters"],
        sorters=request_data.get("sorters", ["name", 1]),
        page=request_data.get("page", 1),
        page_size=request_data.get("page_size", 10),
    )

    return jsonify(crew_array)