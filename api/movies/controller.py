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

def get_movies(filters=None, sorters=None, page=1, page_size=10, search_term=""):
    collection = get_mongo_collection("titlebasics")
    
    if filters is None:
        filters = {}

    if sorters is None:
        sorters = ["_id", -1]

    if search_term:
      filters["primaryTitle"] = {"$regex": search_term, "$options": "i"}

    try:
        # Conta o número total de documentos que correspondem aos filtros
        total_documents = collection.count_documents(filters)

        # Calcula quantos documentos devem ser pulados
        skip = (page - 1) * page_size

        # Busca os documentos na coleção titlelist com os filtros, ordenação, e paginação aplicados
        items = list(
            collection.find(filters)
            .sort(sorters[0], sorters[1])
            .skip(skip)
            .limit(page_size)
        )

        # Converte os ObjectId para strings e sanitiza os dados
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