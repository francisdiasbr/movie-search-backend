from config import get_mongo_collection
from flask import request, jsonify
import math
import requests
from bs4 import BeautifulSoup

from ratings.controller import movie_with_rating_retrieve

def movie_sync(tconst):
    if not tconst:
        return jsonify({"data": "tconst is required"}), 400

    # Verifica se o filme já está sincronizado na coleção
    collection = get_mongo_collection("titlelist")
    existing_movie = collection.find_one({"tconst": tconst})
    if existing_movie:
        return jsonify({"data": "Movie already synced"}), 409
    
    # Recupera informações do filme com avaliação
    movie_info = movie_with_rating_retrieve(tconst)

    if movie_info.get("status") == 404:
        return jsonify({"status": 404, "data": movie_info["data"]}), 404
    elif movie_info.get("status") == 400:
        return jsonify({"status": 400, "data": movie_info["data"]}), 400

    movie_data = movie_info["data"]

    # Obtém a sinopse do filme
    movie_plot = get_movie_plot(tconst)
    movie_data['plot'] = movie_plot

    # Insere as informações na coleção titlelist
    try:
        inserted_id = collection.insert_one(movie_data).inserted_id
        return jsonify({"data": str(inserted_id)}), 201
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to sync movie"}), 500


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


def get_movie_plot(tconst):
    """Obtém a sinopse do filme no IMDb com base no tconst do IMDb"""
    url = f"https://m.imdb.com/title/{tconst}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        plot_span = soup.find("span", {"data-testid": "plot-xs_to_m"})
        if plot_span:
            plot_text = plot_span.get_text().strip()
            return plot_text if plot_text else "Plot not available"
    return "Plot not available"

def get_synced_movies():
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
        return jsonify({"data": "Failed to retrieve synced items"}), 500

def delete_synced_movie(tconst):
    collection = get_mongo_collection("titlelist")
    try:
        result = collection.delete_one({"tconst": tconst})
        if result.deleted_count == 1:
            return jsonify({"data": f"Movie {tconst} deleted"}), 200
        else:
            return jsonify({"data": f"Movie {tconst} not found"}), 404
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to delete synced movie"}), 500