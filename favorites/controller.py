from flask import request, jsonify
import math
import requests
from config import get_mongo_collection, RAPIDAPI_API_KEY
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from favorites.scrapper import (
    get_movie_sm_plot,
    get_movie_quote,
    get_wikipedia_url,
    get_movie_poster,
    get_movie_country,
    get_movie_trivia,
    get_movie_plot_keywords,
    get_director,
    get_movie_genres,
    get_movie_principal_stars,
    get_writers,
)
from movies.controller import get_movie
from spotify.controller import get_album_by_movie_title
from utils import sanitize_movie_data


def get_magnet_link(tconst):
    # Define a URL base
    search_url = f"https://movie_torrent_api1.p.rapidapi.com/search/{tconst}"

    # Define os headers necessários
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-rapidapi-ua": "RapidAPI-Playground",
        "x-rapidapi-key": RAPIDAPI_API_KEY,
        "x-rapidapi-host": "movie_torrent_api1.p.rapidapi.com",
    }

    # print(f"Making request to URL: {search_url}")
    # print(f"Using headers: {headers}")

    # Faz a requisição à API
    response = requests.get(search_url, headers=headers, verify=False)

    print(f"Response Status Code: {response.status_code}")
    print(f"Response Content: {response.text}")

    if response.status_code == 200:
        try:
            data = response.json()
            # print(f"Response JSON: {data}")
            if (
                data["status"] == "success"
                and data.get("data")
                and len(data["data"]) > 0
            ):
                magnet_link = data["data"][0].get("magnet")
                if magnet_link:
                    return {"data": magnet_link}, 200
            return {"data": "Magnet link not found"}, 404
        except ValueError:
            # print("Error decoding JSON.")
            return {"data": "Invalid JSON response from API"}, 500
    else:
        # print(f"Error {response.status_code} - {response.text}")
        return {
            "data": f"Error {response.status_code} - {response.text}"
        }, response.status_code


def favorite_movie(tconst):
    if not tconst:
        print("Error: tconst is required")
        return {"data": "tconst is required"}, 400

    collection_atlas = get_mongo_collection("favoritelist", use_atlas=True)
    collection_local = get_mongo_collection("favoritelist", use_atlas=False)

    # Verificar em ambas as coleções
    existing_movie_atlas = collection_atlas.find_one({"tconst": tconst})
    existing_movie_local = collection_local.find_one({"tconst": tconst})
    
    if existing_movie_atlas or existing_movie_local:
        return {"data": "Movie already listed"}, 409

    movie_info = get_movie(tconst)
    print(f"Retrieved movie info: {movie_info}")

    if movie_info.get("status") == 404:
        print("Movie not found in ratings")
        return {"status": 404, "data": movie_info["data"]}, 404
    elif movie_info.get("status") == 400:
        print("Bad request for movie info")
        return {"status": 400, "data": movie_info["data"]}, 400

    movie_data = movie_info["data"]
    movie_title = movie_data.get("primaryTitle")
    print(f"Movie title: {movie_title}")

    # Funções de scraping a serem executadas em paralelo
    def fetch_data():
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(get_magnet_link, tconst): "magnet_link",
                executor.submit(get_movie_country, tconst): "country",
                executor.submit(get_director, tconst): "director",
                executor.submit(get_movie_genres, tconst): "genres",
                executor.submit(get_movie_sm_plot, tconst): "plot",
                executor.submit(get_movie_plot_keywords, tconst): "plot_keywords",
                executor.submit(get_movie_quote, tconst): "quote",
                executor.submit(get_album_by_movie_title, movie_title): "soundtrack",
                executor.submit(get_movie_principal_stars, tconst): "stars",
                executor.submit(get_movie_trivia, tconst): "trivia",
                executor.submit(get_wikipedia_url, movie_title): "wiki",
                executor.submit(get_writers, tconst): "writers",
            }

            for future in as_completed(futures):
                key = futures[future]
                start_time = time.perf_counter()  # Usa perf_counter para maior precisão
                try:
                    result = future.result()
                    elapsed_time = time.perf_counter() - start_time  # Calcula o tempo decorrido
                    print(f"Tempo para {key}: {elapsed_time:.6f} segundos")  # Mostra mais casas decimais
                    if key == "magnet_link":
                        movie_data[key] = result[0]["data"] if result[1] == 200 else None
                    else:
                        movie_data[key] = result
                except Exception as e:
                    print(f"Error fetching {key}: {e}")
                    movie_data[key] = None

    fetch_data()

    movie_data["watched"] = False

    # Insere as informações na coleção favoritelist
    try:
        result_atlas = collection_atlas.insert_one(movie_data)
        result_local = collection_local.insert_one(movie_data)
        inserted_movie = collection_atlas.find_one({"_id": result_atlas.inserted_id})
        if inserted_movie:
            inserted_movie["_id"] = str(inserted_movie["_id"])
            return {"data": inserted_movie}, 201
        print("Failed to retrieve inserted movie")
        return {"data": "Failed to retrieve inserted movie"}, 500
    except Exception as e:
        print(f"Error during insertion: {e}")
        return {"data": "Failed to list movie"}, 500


# Recupera um filme favoritado
def get_favorited_movie(tconst):
    collection = get_mongo_collection("favoritelist")

    if not tconst:
        return {"data": "tconst is required"}, 400

    try:
        movie = collection.find_one({"tconst": tconst})
        if movie:
            movie["_id"] = str(movie["_id"])
            return {"data": movie}, 200
        else:
            return {"data": "Movie not found"}, 404
    except Exception as e:
        print(f"{e}")
        return {"data": "Failed to retrieve movie"}, 500


# Edita um filme favoritado
def edit_favorited_movie(tconst, soundtrack=None, wiki=None, watched=None):
    collection = get_mongo_collection("favoritelist")
    update_data = {}

    if soundtrack is not None:
        update_data["soundtrack"] = soundtrack
    if wiki is not None:
        update_data["wiki"] = wiki
    if watched is not None:
        update_data["watched"] = watched

    if not update_data:
        return {"data": "No fields to update"}, 400
    try:
        result = collection.update_one({"tconst": tconst}, {"$set": update_data})
        if result.modified_count == 1:
            return {"data": update_data}, 200
        else:
            return {"data": f"Movie {tconst} not found or no changes made"}, 404
    except Exception as e:
        print(f"{e}")
        return {"data": "Failed to update favorited movie"}, 500


# Remove um filme dos favoritos
def delete_favorited_movie(tconst):
    collection = get_mongo_collection("favoritelist")
    try:
        result = collection.delete_one({"tconst": tconst})
        if result.deleted_count == 1:
            return {"data": f"Movie {tconst} deleted"}, 200
        else:
            return {"data": f"Movie {tconst} not found"}, 404
    except Exception as e:
        print(f"{e}")
        return {"data": "Failed to delete listed movie"}, 500


# Recupera os filmes favoritados
def get_favorited_movies(filters={}, sorters=["_id", -1], page=1, page_size=10, search_term=""):
    collection = get_mongo_collection("favoritelist")

    search_term = search_term or filters.get("search_term") or filters.get("tconst")

    # Filtra `search_term` no campo `tconst` ou `primaryTitle`
    if search_term:
        filters["$or"] = [
            {"tconst": search_term},
            {"originalTitle": {"$regex": search_term, "$options": "i"}},
            {"primaryTitle": {"$regex": search_term, "$options": "i"}},
            {"director": {"$regex": search_term, "$options": "i"}},
        ]

    country = filters.get("country")
    if country:
        filters["country"] = country

    unique_countries = collection.distinct("country")
    unique_years = [
        int(year) for year in collection.distinct("startYear") if year is not None
    ]

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

        return {
            "total_documents": total_documents,
            "entries": items,
            "countries": unique_countries,
            "years": unique_years,
        }, 200
    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Internal server error"}, 500
