from config import get_mongo_collection
from flask import request, jsonify
import math
import requests

from list.scrapper import get_movie_sm_plot, get_movie_quote, get_wikipedia_url
from ratings.controller import movie_with_rating_retrieve

def list_movie(tconst):
    if not tconst:
        return jsonify({"data": "tconst is required"}), 400

    # Verifica se o filme já está sincronizado na coleção
    collection = get_mongo_collection("titlelist")
    existing_movie = collection.find_one({"tconst": tconst})
    if existing_movie:
        return jsonify({"data": "Movie already listed"}), 409
    
    # Recupera informações do filme com avaliação
    movie_info = movie_with_rating_retrieve(tconst)

    if movie_info.get("status") == 404:
        return jsonify({"status": 404, "data": movie_info["data"]}), 404
    elif movie_info.get("status") == 400:
        return jsonify({"status": 400, "data": movie_info["data"]}), 400

    movie_data = movie_info["data"]

    # Obtém a sinopse do filme
    movie_plot = get_movie_sm_plot(tconst)
    movie_data['plot'] = movie_plot

    # Obtém a citação do filme
    movie_quote = get_movie_quote(tconst)
    movie_data['quote'] = movie_quote

    # Obtém o endereço da Wikipedia do filme
    movie_title = movie_data.get("primaryTitle")
    movie_wiki = get_wikipedia_url(movie_title)
    movie_data['wiki'] = movie_wiki

    # Insere as informações na coleção titlelist
    try:
        inserted_id = collection.insert_one(movie_data).inserted_id
        return jsonify({"data": str(inserted_id)}), 201
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to list movie"}), 500


def sanitize_movie_data(movie_data):
    """Substitui valores inválidos ou não-serializáveis por valores aceitáveis em JSON."""
    for key, value in movie_data.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            movie_data[key] = None
        elif isinstance(value, list):
            movie_data[key] = [sanitize_movie_data(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            movie_data[key] = sanitize_movie_data(value)
    return movie_data


def get_listed_movies():
    collection = get_mongo_collection("titlelist")
    try:
        # Busca todos os documentos na coleção titlelist
        items = list(collection.find())
        # Converte os ObjectId para strings e sanitiza os dados
        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)
        return jsonify({"data": items}), 200
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to retrieve listed items"}), 500

def delete_listed_movie(tconst):
    collection = get_mongo_collection("titlelist")
    try:
        result = collection.delete_one({"tconst": tconst})
        if result.deleted_count == 1:
            return jsonify({"data": f"Movie {tconst} deleted"}), 200
        else:
            return jsonify({"data": f"Movie {tconst} not found"}), 404
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to delete listed movie"}), 500                                                                                                                          