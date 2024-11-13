from concurrent.futures import ThreadPoolExecutor
from bson import ObjectId
from flask import request, jsonify
import math
import requests
from config import (
    get_mongo_collection,
    RAPIDAPI_API_KEY
)

from favorites.scrapper import (
    get_movie_sm_plot, 
    get_movie_quote, 
    get_wikipedia_url, 
    get_movie_poster, 
    get_movie_country, 
    get_movie_trivia,
    get_movie_plot_keywords,
    get_director
)
from ratings.controller import movie_with_rating_retrieve
from spotify.controller import get_album_by_movie_title
from utils import sanitize_movie_data

def get_magnet_link(tconst):
    collection = get_mongo_collection("favoritelist")
    movie = collection.find_one({"tconst": tconst})
    if not movie:
        return jsonify({"data": "Movie not found"}), 404

    try:
        movie_title = movie.get("originalTitle")
        if not movie_title:
            return jsonify({"data": "Original title not found in the database"}), 404

        search_url = "https://movie_torrent_api1.p.rapidapi.com/search/" + tconst
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-rapidapi-ua": "RapidAPI-Playground",
            "x-rapidapi-key": RAPIDAPI_API_KEY,
            "x-rapidapi-host": "movie_torrent_api1.p.rapidapi.com"
        }

        response = requests.get(search_url, headers=headers, verify=False)

        print(f"Response Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if data["status"] == "success" and data.get("data") and len(data["data"]) > 0:
                    magnet_link = data["data"][0].get("magnet") 
                    if magnet_link:
                        return jsonify({"data": magnet_link}), 200
                return jsonify({"data": "Magnet link not found"}), 404
            except ValueError:
                print("Erro ao decodificar JSON.")
                return jsonify({"data": "Invalid JSON response from API"}), 500
        else:
            return jsonify({"data": f"Error {response.status_code} - {response.text}"}), response.status_code
                
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"data": "Failed to retrieve magnet link"}), 500

def convert_objectid_to_str(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):  # Checar listas dentro do dicionário
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
    return data

# Adiciona um filme à lista de favoritos
def favorite_movie(tconst):
    if not tconst:
        return {"data": "tconst is required"}, 400

    collection = get_mongo_collection("favoritelist")
    existing_movie = collection.find_one({"tconst": tconst})

    if existing_movie:
        return ({"data": "Movie already listed"}), 409
    
    # Recupera informações do filme com avaliação
    movie_info = movie_with_rating_retrieve(tconst)
    if movie_info.get("status") == 404:
        return jsonify({"status": 404, "data": movie_info["data"]}), 404
    elif movie_info.get("status") == 400:
        return jsonify({"status": 400, "data": movie_info["data"]}), 400

    movie_data = movie_info["data"]

    # Funções independentes para execução em paralelo
    with ThreadPoolExecutor() as executor:
        future_plot = executor.submit(get_movie_sm_plot, tconst)
        future_quote = executor.submit(get_movie_quote, tconst)
        future_wiki = executor.submit(get_wikipedia_url, movie_data.get("originalTitle"))
        future_soundtrack = executor.submit(get_album_by_movie_title, movie_data.get("originalTitle"))
        # future_poster = executor.submit(get_movie_poster, tconst)
        future_country = executor.submit(get_movie_country, tconst)
        future_trivia = executor.submit(get_movie_trivia, tconst)
        future_keywords = executor.submit(get_movie_plot_keywords, tconst)
        future_director = executor.submit(get_director, tconst)

        # Aguarda todos os futuros e coleta os resultados
        movie_data['plot'] = future_plot.result()
        movie_data['quote'] = future_quote.result()
        movie_data['wiki'] = future_wiki.result()
        movie_data['soundtrack'] = future_soundtrack.result()
        # movie_data['poster'] = future_poster.result()
        movie_data['country'] = future_country.result()
        movie_data['trivia'] = future_trivia.result()
        movie_data['plot_keywords'] = future_keywords.result()
        movie_data['director'] = future_director.result()

    # Converte qualquer ObjectId em movie_data
    movie_data = convert_objectid_to_str(movie_data)

    try:
        inserted_id = collection.insert_one(movie_data).inserted_id
        movie_data['_id'] = str(inserted_id)  # Converte o ObjectId do insert para string antes de retornar
        return jsonify({"data": movie_data}), 201
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to list movie"}), 500


# Recupera um filme favoritado
def get_favorited_movie(tconst):
    collection = get_mongo_collection("favoritelist")           

    if not tconst:
        return jsonify({"data": "tconst is required"}), 400

    try:
        movie = collection.find_one({"tconst": tconst})
        if movie:
            movie["_id"] = str(movie["_id"])
            return jsonify({"data": movie}), 200
        else:
            return jsonify({"data": "Movie not found"}), 404
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to retrieve movie"}), 500


# Edita um filme favoritado
def edit_favorited_movie(tconst, originalTitle=None, startYear=None, soundtrack=None, wiki=None):
    collection = get_mongo_collection("favoritelist")
    update_data = {}

    if originalTitle is not None:
        update_data["originalTitle"] = originalTitle
    if startYear is not None:
        update_data["startYear"] = startYear
    if soundtrack is not None:
        update_data["soundtrack"] = soundtrack
    if wiki is not None:
        update_data["wiki"] = wiki

    if not update_data:
        return jsonify({"data": "No fields to update"}), 400
    try:
        result = collection.update_one(
            {"tconst": tconst},
            {"$set": update_data}
        )
        if result.modified_count == 1:
            return jsonify({"data": update_data}), 200
        else:
            return jsonify({"data": f"Movie {tconst} not found or no changes made"}), 404
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to update favorited movie"}), 500


# Remove um filme dos favoritos
def delete_favorited_movie(tconst):
    collection = get_mongo_collection("favoritelist")
    try:
        result = collection.delete_one({"tconst": tconst})
        if result.deleted_count == 1:
            return jsonify({"data": f"Movie {tconst} deleted"}), 200
        else:
            return jsonify({"data": f"Movie {tconst} not found"}), 404
    except Exception as e:
        print(f"{e}")
        return jsonify({"data": "Failed to delete listed movie"}), 500      


# Recupera os filmes favoritados
def get_favorited_movies(filters={}, sorters=["_id", -1], page=1, page_size=10, search_term=""):

    collection = get_mongo_collection("favoritelist")

    search_term = search_term or filters.get("search_term") or filters.get("tconst")
    
    # Filtra `search_term` no campo `tconst` ou `originalTitle`
    if search_term:
        filters["$or"] = [
            {"tconst": search_term},
            {"originalTitle": {"$regex": search_term, "$options": "i"}}
        ]
    
    country = filters.get('country')
    if country:
        filters['country'] = country
    else:
        filters.pop("country", None)  # Remove o filtro `country` se estiver vazio


    unique_countries = collection.distinct("country")
    unique_years = [int(year) for year in collection.distinct("startYear") if year is not None]

    start_year = filters.get("startYear")
    if start_year:
        try:
            start_year = int(start_year)
            filters["startYear"] = start_year
        except (TypeError, ValueError):
            filters.pop("startYear", None)
            print("Warning: startYear provided is not a valid number.")
    else:
        filters["startYear"] = {"$exists": True, "$ne": None, "$nin": [float('NaN')], "$gt": 1940}

    try:
        total_documents = collection.count_documents(filters)
        skip = (page - 1) * page_size
        items = list(
            collection.find(filters)
            .sort(sorters[0], sorters[1])
            .skip(skip)
            .limit(page_size)
        )

        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        return jsonify({
            "total_documents": total_documents,
            "entries": items,
            "countries": unique_countries,
            "years": unique_years
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": 500, "message": "Internal server error"}), 500