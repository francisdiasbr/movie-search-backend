from flask import (
    jsonify,
    request
)
import json

from config import get_mongo_collection
from utils import sanitize_movie_data
from bson import ObjectId

authoralreviewslist_collection = get_mongo_collection("authoralreviewslist")
favoritelist_collection = get_mongo_collection("favoritelist")


# Cria e salva uma resenha para um filme
def create_and_save_movie_review(tconst):

    movie = favoritelist_collection.find_one({"tconst": tconst})

    review_data = request.json.get("data", {})
    author = review_data.get("author", "")
    review = review_data.get("review", "")
    reviewTitle = review_data.get("reviewTitle", "")

    if not movie:
        return {"status": 404, "message": "Movie not found"}

    review_document = {
        "tconst": tconst,
        "reviewTitle": reviewTitle,
        "review": review,
        "author": author
    }
    
    try:
        result = authoralreviewslist_collection.insert_one(review_document)

        review_document["_id"] = str(result.inserted_id)

        return {"data": review_document}

    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Internal server error"}


# Obtém uma resenha específica
def get_movie_review(tconst):
    try:
        # Buscar todas as reviews para o tconst específico
        movie_reviews = list(authoralreviewslist_collection.find(
            {"tconst": tconst},
            {"_id": 1, "tconst": 1, "reviewTitle": 1, "review": 1, "author": 1}
        ))

        # Converter ObjectId para string em cada review
        for review in movie_reviews:
            review["_id"] = str(review["_id"])

        if movie_reviews:
            return {
                "total_documents": len(movie_reviews),
                "entries": movie_reviews
            }, 200
        else:
            return {"status": 404, "message": "No reviews found for this movie"}
    
    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Internal server error"}


# Atualiza uma resenha existente
def edit_movie_review(tconst, review_id, reviewTitle=None, author=None, review=None):
    try:
        # Primeiro verifica se a review existe usando tconst e _id
        existing_review = authoralreviewslist_collection.find_one({
            "tconst": tconst,
            "_id": ObjectId(review_id)
        })
        
        if not existing_review:
            return {"status": 404, "message": f"Review not found"}

        # Prepara os dados para atualização
        update_data = {}
        if reviewTitle is not None:
            update_data["reviewTitle"] = reviewTitle
        if author is not None:
            update_data["author"] = author
        if review is not None:
            update_data["review"] = review

        # Atualiza o documento específico
        result = authoralreviewslist_collection.update_one(
            {
                "tconst": tconst,
                "_id": ObjectId(review_id)
            }, 
            {"$set": update_data}
        )

        if result.modified_count == 1:
            # Busca a review atualizada para retornar
            updated_review = authoralreviewslist_collection.find_one({
                "tconst": tconst,
                "_id": ObjectId(review_id)
            })
            updated_review["_id"] = str(updated_review["_id"])
            return {"data": updated_review}, 200
        else:
            return {"status": 400, "message": "No changes were made"}

    except Exception as e:
        print(f"Error updating review: {e}")
        return {"status": 500, "message": "Failed to update review"}


# Remove uma resenha da base
def delete_movie_review(tconst, review_id):
    try:
        result = authoralreviewslist_collection.delete_one({
            "tconst": tconst,
            "_id": ObjectId(review_id)
        })
        
        if result.deleted_count == 1:
            return {"message": f"Review deleted successfully"}, 200
        else:
            return {"status": 404, "message": "Review not found"}, 404
    except Exception as e:
        print(f"Error deleting review: {e}")
        return {"status": 500, "message": "Failed to delete review"}, 500


# Recupera as resenhas criadas
def get_created_reviews(filters={}, sorters=["_id", -1], page=1, page_size=10):
    collection = authoralreviewslist_collection

    try:
        total_documents = collection.count_documents(filters)
        skip = (page - 1) * page_size
        items = list(
            collection.find(filters)
            .sort(sorters[0], sorters[1])
            .skip(skip)
            .limit(page_size)
        )

        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        return {
            "total_documents": total_documents,
            "entries": items
        }, 200
    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Internal server error"}, 500
        