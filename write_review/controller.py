import logging
from datetime import datetime

import db
from config import FAVORITES_COLLECTION, REVIEWS_COLLECTION, get_mongo_collection
from utils import error, pick

logger = logging.getLogger(__name__)

# Fields the client may change on a review.
EDITABLE_FIELDS = ("content", "references", "images")


def reviews():
    return get_mongo_collection(REVIEWS_COLLECTION)


def create_and_save_movie_review(tconst, review_data):
    movie = get_mongo_collection(FAVORITES_COLLECTION).find_one({"tconst": tconst})
    if not movie:
        return error("Filme não encontrado nos favoritos", 404)

    collection = reviews()
    if collection.find_one({"tconst": tconst}):
        return error("Já existe uma resenha para este filme", 409)

    review_data = review_data or {}
    if not review_data.get("content", {}).get("pt", {}).get("text"):
        return error("Conteúdo da review é obrigatório", 400)

    review = db.insert(
        collection,
        {
            "tconst": tconst,
            "content": review_data["content"],
            "created_at": datetime.now().isoformat(),
            "isAiGenerated": review_data.get("isAiGenerated", False),
            "references": review_data.get("references", []),
            "images": review_data.get("images", []),
            "primaryTitle": movie.get("primaryTitle", ""),
        },
    )
    logger.info("Review created for %s", tconst)
    return {"data": review}, 201


def get_movie_review(tconst):
    total, entries = db.search(reviews(), {"tconst": tconst})
    if not entries:
        return error("No reviews found for this movie", 404)
    return {"total_documents": total, "entries": entries}, 200


def edit_movie_review(tconst, request_data):
    """Updates only the fields present in the body; the others are kept."""
    review = db.update(reviews(), {"tconst": tconst}, pick(request_data, EDITABLE_FIELDS))
    if not review:
        return error("Review not found", 404)
    return {"data": review}, 200


def delete_movie_review(tconst):
    if not db.delete(reviews(), {"tconst": tconst}):
        return error("Review not found", 404)
    return {"message": "Review deleted successfully"}, 200


def get_created_reviews(filters=None):
    total, entries = db.search(reviews(), filters)
    return {"total_documents": total, "entries": entries}, 200
