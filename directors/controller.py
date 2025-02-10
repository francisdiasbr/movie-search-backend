from flask import request, jsonify
import os
from config import get_mongo_collection
from .utils import get_director_info
import time  # Adicione esta importação

COLLECTION_NAME = "favorites_directors"


def add_director(director, api_key, model):
    """Adiciona um diretor aos favoritos e recupera sua filmografia"""
    start_time = time.perf_counter()

    if not director:
        return {"data": "Director is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    existing_director = collection.find_one({"director": director})
    if existing_director:
        return {"data": "Director already listed"}, 409

    try:
        director_info_response, status_code = get_director_info(api_key, director, model)
        
        if status_code != 200:
            return director_info_response, status_code

        director_data = director_info_response.get("data")
        if not director_data or not isinstance(director_data, dict):
            return {"data": "Invalid response format from LLM"}, 500

        if "movies" not in director_data or "personal_info" not in director_data:
            return {"data": "Missing required fields in LLM response"}, 500
        
        insert_data = {
            "director": director,
            "filmography": director_data["movies"],
            "personal_info": director_data["personal_info"]
        }
        
        result = collection.insert_one(insert_data)
        inserted_director = collection.find_one({"_id": result.inserted_id})
        
        if not inserted_director:
            return {"data": "Failed to add director"}, 500

        elapsed_time = time.perf_counter() - start_time
        print(f"Tempo total: {elapsed_time:.6f} segundos")
        
        return {
            "data": {
                "_id": str(inserted_director["_id"]),
                "director": inserted_director["director"],
                "filmography": inserted_director["filmography"],
                "personal_info": inserted_director["personal_info"]
            }
        }, 201
            
    except Exception as e:
        print(f"Error processing director info: {str(e)}")
        return {"data": f"Error processing director information: {str(e)}"}, 500


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


def get_director_details(director):
    """Recupera todas as propriedades de um diretor específico"""

    if not director:
        return {"data": "Director is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    try:
        director_data = collection.find_one({"director": director})
        if director_data:
            # Converte ObjectId para string
            director_data["_id"] = str(director_data["_id"])
            return {"data": director_data}, 200
        return {"data": "Director not found"}, 404
    except Exception as e:
        print(f"Error: {e}")
        return {"data": "Failed to retrieve director details"}, 500



