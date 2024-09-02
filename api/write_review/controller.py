from flask import (
    jsonify,
    request
)
import json

from config import get_mongo_collection
from utils import sanitize_movie_data

authoralreviewslist_collection = get_mongo_collection("authoralreviewslist")
favoritelist_collection = get_mongo_collection("favoritelist")

def create_and_save_movie_review(tconst):

    movie = favoritelist_collection.find_one({"tconst": tconst})

    review_data = request.json
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


def get_movie_review(tconst):
    try:
        movie_review = authoralreviewslist_collection.find_one({"tconst": tconst}, {"_id": 0})
        if movie_review:
            return {"data": movie_review}
        else:
            return {"status": 404, "message": "Review not found"}
    
    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Internal server error"}


def edit_movie_review(tconst, reviewTitle=None, author=None, review=None):
    
    update_data = {}

    if reviewTitle is not None:
        update_data["reviewTitle"] = reviewTitle
    
    if author is not None:
        update_data["author"] = author
    
    if review is not None:
        update_data["review"] = review

    try:
        result = authoralreviewslist_collection.update_one(
            {"tconst": tconst}, 
            {"$set": update_data}
        )
        if result.modified_count == 1:
            return jsonify({"data": update_data}), 200
        else:
            return jsonify({"data": f"Review {tconst} not found or no changes made"}, 404)
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to update review"}, 500)

# Remove uma resenha da base
def delete_movie_review(tconst):
    try:
        result = authoralreviewslist_collection.delete_one({"tconst": tconst})
        if result.deleted_count == 1:
            return jsonify({"data": f"Review {tconst} deleted"}), 200
        else:
            return jsonify({"data": f"Review {tconst} not found"}), 404
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to delete review"}), 500

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

        return jsonify({
            "total_documents": total_documents,
            "entries": items
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": 500, "message": "Internal server error"}), 500
        