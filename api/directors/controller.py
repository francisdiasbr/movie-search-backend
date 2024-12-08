from flask import request, jsonify
import os
from config import get_mongo_collection
from .utils import get_director_info
import time  # Adicione esta importação

COLLECTION_NAME = "favorites_directors"


def add_director(director, api_key, model):
    """Adiciona um diretor aos favoritos e recupera sua filmografia"""
    start_time = time.perf_counter()  # Início da medição de tempo

    if not director:
        return {"data": "Director is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    # Verifica se o diretor já está na lista de diretores favoritos
    existing_director = collection.find_one({"director": director})
    if existing_director:
        return {"data": "Director already listed"}, 409

    # Chama a função para recuperar a filmografia e informações pessoais do diretor
    director_info_response = get_director_info(api_key, director, model)

    # Verifica se a recuperação da filmografia foi bem-sucedida
    if director_info_response[1] != 200:
        return {"data": "Failed to retrieve filmography"}, 500

    director_info = director_info_response[0].get("data")

    # Insere o novo diretor com a filmografia e informações pessoais
    try:
        director_data = {
            "director": director,
            "filmography": director_info.get("movies", []),
            "personal_info": director_info.get("personal_info", {})
        }
        result = collection.insert_one(director_data)
        inserted_director = collection.find_one({"_id": result.inserted_id})
        if inserted_director:
            elapsed_time = time.perf_counter() - start_time  # Fim da medição de tempo
            print(f"Tempo para adicionar diretor e recuperar filmografia: {elapsed_time:.6f} segundos")
            return {
                "data": {
                    "_id": str(inserted_director["_id"]),
                    "director": inserted_director["director"],
                    "filmography": inserted_director.get("filmography", []),
                    "personal_info": inserted_director.get("personal_info", {})
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



