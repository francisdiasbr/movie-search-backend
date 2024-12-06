from flask import request, jsonify
from config import get_mongo_collection

COLLECTION_NAME = "favorites_directors"


def add_director(director):
    """Adiciona um diretor aos favoritos"""

    if not director:
        return {"data": "Director is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    # Verifica se o diretor já está na lista de diretores favoritos
    existing_director = collection.find_one({"director": director})
    if existing_director:
        return {"data": "Director already listed"}, 409

    # Insere o novo diretor
    try:
        result = collection.insert_one({"director": director})
        inserted_director = collection.find_one({"_id": result.inserted_id})
        if inserted_director:
            return {
                "data": {
                    "_id": str(inserted_director["_id"]),
                    "director": inserted_director["director"],
                }
            }, 201
        return {"data": "Failed to retrieve inserted director"}, 500
    except Exception as e:
        print(f"Error: {e}")
        return {"data": "Failed to add director"}, 500


def get_favorited_directors():
    """Recupera todos os diretores favoritos"""

    collection = get_mongo_collection(COLLECTION_NAME)

    try:
        directors = list(collection.find({}, {"_id": 1, "director": 1}))
        # Converte ObjectId para string
        for director in directors:
            director["_id"] = str(director["_id"])
        return {"data": directors}, 200
    except Exception as e:
        print(f"Error: {e}")
        return {"data": "Failed to retrieve directors"}, 500


def delete_favorited_director(director):
    """Remove um diretor dos favoritos"""

    if not director:
        return {"data": "Director is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    try:
        result = collection.delete_one({"director": director})
        if result.deleted_count:
            return {"data": "Director deleted successfully"}, 200
        return {"data": "Director not found"}, 404
    except Exception as e:
        print(f"Error: {e}")
        return {"data": "Failed to delete director"}, 500
