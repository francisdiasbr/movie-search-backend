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

# Recupera o magnet link do filme
def get_magnet_link(tconst):
    # Define a URL base
    search_url = f"https://movie_torrent_api1.p.rapidapi.com/search/{tconst}"
    
    # Define os headers necessários
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-rapidapi-ua": "RapidAPI-Playground",
        "x-rapidapi-key": RAPIDAPI_API_KEY,
        "x-rapidapi-host": "movie_torrent_api1.p.rapidapi.com"
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
            if data["status"] == "success" and data.get("data") and len(data["data"]) > 0:
                magnet_link = data["data"][0].get("magnet")
                if magnet_link:
                    return {"data": magnet_link}, 200
            return {"data": "Magnet link not found"}, 404
        except ValueError:
            # print("Error decoding JSON.")
            return {"data": "Invalid JSON response from API"}, 500
    else:
        # print(f"Error {response.status_code} - {response.text}")
        return {"data": f"Error {response.status_code} - {response.text}"}, response.status_code



# Adiciona um filme à lista de favoritos
def favorite_movie(tconst):
    if not tconst:
        print("Error: tconst is required")  # Log para tconst ausente
        return {"data": "tconst is required"}, 400

    collection = get_mongo_collection("favoritelist")

    # Verifica se o filme já está na lista de favoritos
    existing_movie = collection.find_one({"tconst": tconst})
    print(f"Checking if movie with tconst {tconst} already exists: {existing_movie is not None}")  # Log para verificação de duplicatas
    
    if existing_movie:
        return {"data": "Movie already listed"}, 409
    
    # Recupera informações do filme com avaliação
    movie_info = movie_with_rating_retrieve(tconst)
    print(f"Retrieved movie info: {movie_info}")  # Log para informações do filme

    if movie_info.get("status") == 404:
        print("Movie not found in ratings")  # Log para filme não encontrado
        return {"status": 404, "data": movie_info["data"]}, 404
    elif movie_info.get("status") == 400:
        print("Bad request for movie info")  # Log para requisição inválida
        return {"status": 400, "data": movie_info["data"]}, 400

    movie_data = movie_info["data"]

    movie_title = movie_data.get("primaryTitle")
    print(f"Movie title: {movie_title}")  

    # Recupera o magnet link do filme
    magnet_link_response = get_magnet_link(tconst)
    print(f"Magnet link response: {magnet_link_response}")  
    if magnet_link_response[1] != 200:
        print("Failed to retrieve magnet link")
        return {"data": "Failed to retrieve magnet link"}, magnet_link_response[1]

    # Adiciona informações do filme
    movie_data['country'] = get_movie_country(tconst)
    movie_data['director'] = get_director(tconst)
    movie_data['magnet_link'] = magnet_link_response[0]['data']
    movie_data['plot'] = get_movie_sm_plot(tconst)
    movie_data['plot_keywords'] = get_movie_plot_keywords(tconst)
    movie_data['quote'] = get_movie_quote(tconst)
    movie_data['soundtrack'] = get_album_by_movie_title(movie_title)
    movie_data['trivia'] = get_movie_trivia(tconst)
    movie_data['wiki'] = get_wikipedia_url(movie_title)

    # Insere as informações na coleção favoritelist
    try:
        result = collection.insert_one(movie_data)
        # Recupera o documento inserido
        inserted_movie = collection.find_one({"_id": result.inserted_id})
        if inserted_movie:
            inserted_movie["_id"] = str(inserted_movie["_id"])
            return {"data": inserted_movie}, 201
        print("Failed to retrieve inserted movie")  # Log para falha na recuperação do filme inserido
        return {"data": "Failed to retrieve inserted movie"}, 500
    except Exception as e:
        print(f"Error during insertion: {e}")  # Log para erro durante a inserção
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
def edit_favorited_movie(tconst, primaryTitle=None, startYear=None, soundtrack=None, wiki=None):
    collection = get_mongo_collection("favoritelist")
    update_data = {}

    if primaryTitle is not None:
        update_data["primaryTitle"] = primaryTitle
    if startYear is not None:
        update_data["startYear"] = startYear
    if soundtrack is not None:
        update_data["soundtrack"] = soundtrack
    if wiki is not None:
        update_data["wiki"] = wiki

    if not update_data:
        return {"data": "No fields to update"}, 400
    try:
        result = collection.update_one(
            {"tconst": tconst},
            {"$set": update_data}
        )
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
    
    country = filters.get('country')
    if country:
        filters['country'] = country

    if search_term:
      filters["primaryTitle"] = {"$regex": search_term, "$options": "i"}


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
            "entries": items
        }, 200
    except Exception as e:
        print(f"Error: {e}")
        return {
            "status": 500,
            "message": "Internal server error"
        }, 500