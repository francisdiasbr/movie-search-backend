from config import get_mongo_collection
import math
from datetime import datetime


# Substitui valores inválidos ou não-serializáveis por valores aceitáveis em JSON
def sanitize_movie_data(movie_data):
    for key, value in movie_data.items():
        if key == "startYear":
            # Verifica se startYear é um número válido
            if (
                not isinstance(value, (int, float))
                or value is None
                or math.isnan(value)
                or math.isinf(value)
            ):
                movie_data[key] = None
        elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            movie_data[key] = None
        elif isinstance(value, list):
            movie_data[key] = [
                sanitize_movie_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, dict):
            movie_data[key] = sanitize_movie_data(value)
    return movie_data


# Pesquisa os filmes da base de dados
def get_movies(filters=None, sorters=None, page=1, page_size=10, search_term=""):
    collection = get_mongo_collection("moviebasics")

    if filters is None:
        filters = {}

    if sorters is None:
        sorters = ["_id", -1]

    filters["startYear"] = {
        "$exists": True,
        "$ne": None,
        "$nin": [float("NaN")],
        "$gt": 1940,
    }

    if search_term:
        filters["$or"] = [
            {"tconst": search_term},
            {"originalTitle": {"$regex": search_term, "$options": "i"}},
            {"primaryTitle": {"$regex": search_term, "$options": "i"}},
        ]

    try:
        date_start1 = datetime.now()
        total_documents = collection.count_documents(filters)
        print(
            f"Tempo de execução: {(datetime.now() - date_start1).total_seconds()} segundos"
        )

        skip = (page - 1) * page_size

        date_start2 = datetime.now()
        items = list(
            collection.find(filters)
            .sort(sorters[0], sorters[1])
            .skip(skip)
            .limit(page_size)
        )

        # Filtra manualmente para garantir que startYear é um número válido
        items = [
            item
            for item in items
            if isinstance(item.get("startYear"), (int, float))
            and item["startYear"] is not None
        ]

        print(
            f"Tempo de execução: {(datetime.now() - date_start2).total_seconds()} segundos"
        )

        date_start3 = datetime.now()
        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        print(
            f"Tempo de execução: {(datetime.now() - date_start3).total_seconds()} segundos"
        )

        # Retorna diretamente o dicionário, não um objeto Response
        return {"total_documents": total_documents, "entries": items}

    except Exception as e:
        print(f"Error: {e}")
        # Retorna um dicionário de erro
        return {"status": 500, "message": "Internal server error"}, 500
