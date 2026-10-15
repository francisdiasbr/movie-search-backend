from datetime import datetime
import logging

from pymongo import ReturnDocument

from config import get_mongo_collection
from utils import sanitize_movie_data, sanitize_filters

logger = logging.getLogger(__name__)

COLLECTION = "authoralreviewslist"


def reviews():
    return get_mongo_collection(COLLECTION)


# Cria e salva uma resenha para um filme
def create_and_save_movie_review(tconst, review_data):
    """Cria e salva uma resenha para um filme"""
    try:
        movie = get_mongo_collection("favoritelist").find_one({"tconst": tconst})
        if not movie:
            return {"status": 404, "message": "Filme não encontrado nos favoritos"}, 404

        collection = reviews()
        if collection.find_one({"tconst": tconst}):
            return {"status": 409, "message": "Já existe uma resenha para este filme"}, 409

        if not review_data or not review_data.get("content", {}).get("pt", {}).get("text"):
            return {"status": 400, "message": "Conteúdo da review é obrigatório"}, 400

        review_document = {
            "tconst": tconst,
            "content": review_data.get("content", {}),
            "created_at": datetime.now().isoformat(),
            "isAiGenerated": review_data.get("isAiGenerated", False),
            "references": review_data.get("references", []),
            "images": review_data.get("images", []),
            "primaryTitle": movie.get("primaryTitle", ""),
        }

        review_document["_id"] = str(collection.insert_one(review_document).inserted_id)
        logger.info("Review created for %s", tconst)
        return {"data": review_document}, 201
    except Exception as e:
        logger.error("Could not create review for %s: %s", tconst, e)
        return {"status": 500, "message": str(e)}, 500


# Obtém uma resenha específica
def get_movie_review(tconst):
    try:
        movie_reviews = list(reviews().find({"tconst": tconst}))

        for review in movie_reviews:
            review["_id"] = str(review["_id"])

        if movie_reviews:
            return {
                "total_documents": len(movie_reviews),
                "entries": movie_reviews,
            }, 200
        else:
            return {"message": "No reviews found for this movie"}, 404

    except Exception as e:
        logger.error("Could not fetch review of %s: %s", tconst, e)
        return {"message": "Internal server error"}, 500


# Atualiza uma resenha existente
def edit_movie_review(tconst, request_data):
    """Atualiza uma resenha específica"""
    try:
        # Verifica se a review existe usando tconst
        collection = reviews()
        existing_review = collection.find_one({"tconst": tconst})

        if not existing_review:
            return {"message": "Review not found"}, 404

        # Campos permitidos para atualização
        update_data = {
            "content": request_data.get("content"),
            "references": request_data.get("references"),
            "images": request_data.get("images"),
        }

        # Remove campos None do update_data
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            return {"message": "No valid fields to update"}, 400

        # Saving the same text again is a valid request, so the document is
        # returned regardless of whether anything actually changed.
        updated_review = collection.find_one_and_update(
            {"tconst": tconst},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )
        updated_review["_id"] = str(updated_review["_id"])
        return {"data": updated_review}, 200

    except Exception as e:
        logger.error("Could not update review of %s: %s", tconst, e)
        return {"message": "Failed to update review"}, 500


# Remove uma resenha da base
def delete_movie_review(tconst):
    """Remove uma resenha da base usando apenas o tconst"""
    try:
        if reviews().delete_one({"tconst": tconst}).deleted_count == 0:
            return {"status": 404, "message": "Review not found"}, 404
        return {"message": "Review deleted successfully"}, 200
    except Exception as e:
        logger.error("Could not delete review of %s: %s", tconst, e)
        return {"status": 500, "message": "Failed to delete review"}, 500


# Recupera as resenhas criadas
def get_created_reviews(filters={}, sorters=["_id", -1]):
    collection = reviews()

    try:
        sanitized_filters = sanitize_filters(filters)

        total_documents = collection.count_documents(sanitized_filters)
        items = list(
            collection.find(sanitized_filters)
            .sort(sorters[0], sorters[1])
        )

        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        return {"total_documents": total_documents, "entries": items}, 200
    except Exception as e:
        logger.error("Could not search reviews: %s", e)
        return {"status": 500, "message": "Internal server error"}, 500
