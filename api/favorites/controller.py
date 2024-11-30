from flask import request, jsonify
import math
import requests
from config import get_mongo_collection

from favorites.scrapper import (
    get_movie_sm_plot, 
    get_movie_quote, 
    get_wikipedia_url, 
    get_movie_poster, 
    get_movie_country, 
    get_movie_trivia
)
from ratings.controller import movie_with_rating_retrieve
from spotify.controller import get_album_by_movie_title
from utils import sanitize_movie_data


# Adiciona um filme à lista de favoritos
def favorite_movie(tconst):
    if not tconst:
        return {"data": "tconst is required"}, 400

    collection = get_mongo_collection("favoritelist")

    existing_movie = collection.find_one({"tconst": tconst})
    
    if existing_movie:
        return {"data": "Movie already listed"}, 409
    
    # Recupera informações do filme com avaliação
    movie_info = movie_with_rating_retrieve(tconst)

    if movie_info.get("status") == 404:
        return {"status": 404, "data": movie_info["data"]}, 404
    elif movie_info.get("status") == 400:
        return {"status": 400, "data": movie_info["data"]}, 400

    movie_data = movie_info["data"]

    movie_plot = get_movie_sm_plot(tconst)
    movie_quote = get_movie_quote(tconst)
    movie_title = movie_data.get("primaryTitle")
    movie_wiki = get_wikipedia_url(movie_title)
    movie_soundtrack = get_album_by_movie_title(movie_title)
    movie_poster = get_movie_poster(tconst)
    movie_country = get_movie_country(tconst)
    movie_trivia = get_movie_trivia(tconst)

    movie_data['plot'] = movie_plot
    movie_data['quote'] = movie_quote
    movie_data['wiki'] = movie_wiki
    movie_data['soundtrack'] = movie_soundtrack
    movie_data['poster'] = movie_poster
    movie_data['country'] = movie_country
    movie_data['trivia'] = movie_trivia

    # Insere as informações na coleção favoritelist
    try:
        result = collection.insert_one(movie_data)
        # Recupera o documento inserido
        inserted_movie = collection.find_one({"_id": result.inserted_id})
        if inserted_movie:
            inserted_movie["_id"] = str(inserted_movie["_id"])
            return {"data": inserted_movie}, 201
        return {"data": "Failed to retrieve inserted movie"}, 500
    except Exception as e:
        print(f"{e}")
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