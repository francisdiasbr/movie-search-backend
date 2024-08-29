from config import get_mongo_collection
from flask import request, jsonify
import math


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


def get_details_movie():
    tconst = request.args.get('tconst')
    
    if not tconst:
        return jsonify({"data": "tconst is required"}), 400

    # Conecta à coleção titlelist
    collection = get_mongo_collection("favoritelist")
    
    try:
        # Busca o filme na coleção pelo tconst
        movie = collection.find_one({"tconst": tconst})
        
        if not movie:
            return jsonify({"data": "Movie not found"}), 404
        
        # Sanitiza os dados e converte o ObjectId para string
        movie["_id"] = str(movie["_id"])
        sanitize_movie_data(movie)
        
        return jsonify({"data": movie}), 200
    
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to retrieve movie details"}), 500
