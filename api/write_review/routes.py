from flask import (
  Blueprint,
  jsonify,
  request
)

from write_review.controller import (
  create_and_save_movie_review,
  delete_movie_review,
  edit_movie_review,
  get_movie_review,
  get_created_reviews
)

write_review_bp = Blueprint("write_review", __name__)

# salva a resenha criada pelo usuário para um filme existente na base de favoritos
@write_review_bp.route("/favorited-movies/<tconst>/write-review", methods=["POST"])
def create_review(tconst):
    return create_and_save_movie_review(tconst)

  
@write_review_bp.route("/favorited-movies/<tconst>/write-review", methods=["GET"])
def get_review(tconst):
    result = get_movie_review(tconst)


@write_review_bp.route("/favorited-movies/<tconst>/write-review", methods=["PUT"])
def update_review(tconst):      

  request_data = request.get_json()
  print('request_data', request_data)
  title = request_data.get("reviewTitle")
  author = request_data.get("author")
  review = request_data.get("review")

  return edit_movie_review(tconst, title, author, review)

  if result["status"] == 200:
    return jsonify({"message": result["message"]}), 200
  elif result["status"] == 404:
    return jsonify({"message": result["message"]}), 404
  else:
    return jsonify({"message": result["message"]}), 500


@write_review_bp.route("/favorited-movies/<tconst>/write-review", methods=["DELETE"])
def delete_review(tconst):
  return delete_movie_review(tconst)

  if result["status"] == 200:
    return jsonify({"message": result["message"]}), 200
  elif result["status"] == 404:
    return jsonify({"message": result["message"]}), 404
  else:
    return jsonify({"message": result["message"]}), 500

@write_review_bp.route("/favorited-movies/write-review/search", methods=["POST"])
def retrieve_created_reviews():
  request_data = request.get_json()
  if not isinstance(request_data, dict):
    return jsonify({"status": 400, "message": "Invalid input data"}), 400
  search_array = get_created_reviews(
    filters=request_data.get("filters", {}),
    page=request_data.get("page", 1),
    page_size=request_data.get("page_size", 10),
  )
  return search_array