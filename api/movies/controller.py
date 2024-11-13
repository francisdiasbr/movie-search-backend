from config import get_mongo_collection
from flask import request, jsonify
import math

from datetime import datetime

# Substitui valores inválidos ou não-serializáveis por valores aceitáveis em JSON
def sanitize_movie_data(movie_data):
    for key, value in movie_data.items():
        if key == "startYear":
            # Verifica se startYear é um número válido
            if not isinstance(value, (int, float)) or value is None or math.isnan(value) or math.isinf(value):
                movie_data[key] = None
            else:
                # Converte startYear para inteiro, caso seja um número float
                movie_data[key] = int(value)
        elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            movie_data[key] = None
        elif isinstance(value, list):
            movie_data[key] = [sanitize_movie_data(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            movie_data[key] = sanitize_movie_data(value)
    return movie_data

# Pesquisa os filmes da base de dados
def get_movies(filters=None, sorters=None, page=1, page_size=10, search_term=""):
    
    collection = get_mongo_collection("titlebasics")
    
    # Atualize para pegar o `search_term` do request
    if filters is None:
        filters = {}

    search_term = search_term or filters.get("search_term")
    
    if search_term:
        filters["$or"] = [
            {"tconst": search_term},
            {"originalTitle": {"$regex": search_term, "$options": "i"}},
            {"primaryTitle": {"$regex": search_term, "$options": "i"}}
        ]

    start_year_filter = filters.get("startYear")
    if start_year_filter is not None:
        try:
            start_year = int(start_year_filter)
            filters["startYear"] = {
                "$exists": True,
                "$ne": None,
                "$nin": [float('NaN')],
                "$eq": start_year
            }
        except (TypeError, ValueError):
            filters.pop("startYear", None)
            print("Warning: startYear provided is not a valid number.")
    else:
        filters["startYear"] = {"$exists": True, "$ne": None, "$nin": [float('NaN')], "$gt": 1940}

    try:
        skip = (page - 1) * page_size
        items = list(
            collection.find(filters)
            .sort(sorters)
            .skip(skip)
            .limit(page_size)
        )

        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        total_documents = (page - 1) * page_size + len(items)

        return jsonify({
            "total_documents": total_documents,
            "entries": items
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": 500, "message": "Internal server error"}), 500
