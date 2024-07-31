from config import get_mongo_collection
from flask import request, jsonify
import math
import requests
from bs4 import BeautifulSoup

from ratings.controller import movie_with_rating_retrieve

def movie_sync():
    # Obtém o item_id dos parâmetros da URL
    item_id = request.args.get("item_id")
    
    if not item_id:
        return jsonify({"status": 400, "data": "Item ID is required"}), 400

    # Recupera informações do filme com avaliação
    movie_info = movie_with_rating_retrieve(item_id)

    if movie_info.get("status") == 404:
        return jsonify({"status": 404, "data": movie_info["data"]}), 404
    elif movie_info.get("status") == 400:
        return jsonify({"status": 400, "data": movie_info["data"]}), 400

    movie_data = movie_info["data"]

    # Insere as informações na coleção titlelist
    collection = get_mongo_collection("titlelist")
    try:
        inserted_id = collection.insert_one(movie_data).inserted_id
        return jsonify({"status": 201, "data": str(inserted_id)}), 201
    except Exception as e:
        print(f"{e}")
        return jsonify({"status": 500, "data": "Failed to sync movie"}), 500

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

def get_synced_items():
    collection = get_mongo_collection("titlelist")
    try:
        # Busca todos os documentos na coleção titlelist
        items = list(collection.find())
        # Converte os ObjectId para strings
        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)
        return jsonify({"data": items}), 200
    except Exception as e:
        print(f"{e}")
        return jsonify({"status": 500, "data": "Failed to retrieve synced items"}), 500
