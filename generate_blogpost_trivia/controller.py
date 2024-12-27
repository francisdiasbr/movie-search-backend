from flask import request, jsonify
import os
from config import get_mongo_collection
from .utils import generate_blog_post_trivia
from favorites.scrapper import get_movie_poster
import time
from datetime import datetime

COLLECTION_NAME = "blogposts_trivia"

def create_and_save_blog_post_trivia(tconst, api_key, model, temperature=0.4, max_tokens=1500):
    """Cria e salva uma postagem de blog para um filme favoritado"""
    start_time = time.perf_counter()

    favoritelist_collection = get_mongo_collection("favoritelist")
    
    movie = favoritelist_collection.find_one({"tconst": tconst})
    if not movie:
        return {"status": 404, "message": "Filme não encontrado nos favoritos"}, 404

    # Chama a função para gerar o trivia da postagem de blog
    blog_post_trivia_response = generate_blog_post_trivia(api_key, movie, model, temperature, max_tokens)

    # Verifica se a geração da postagem foi bem-sucedida
    if blog_post_trivia_response[1] != 200:
        return {"status": 500, "message": "Erro ao gerar postagem do blog"}, 500

    blog_post_trivia = blog_post_trivia_response[0].get("data")

    # Obtém a URL do pôster do filme
    poster_url = get_movie_poster(tconst)

    print(f"Poster URL: {poster_url}")

    creation_timestamp = datetime.now().isoformat()
    # Nova estrutura de dados
    blog_data = {
        "tconst": tconst,
        "primaryTitle": movie.get("primaryTitle"),
        "director_history": blog_post_trivia.get("director_history"),
        "director_quotes": blog_post_trivia.get("director_quotes"),
        "curiosities": blog_post_trivia.get("curiosities"),
        "reception": blog_post_trivia.get("reception"),
        "highlights": blog_post_trivia.get("highlights"),
        "plot": blog_post_trivia.get("plot"),
    }

    try:
        # Obtém ambas as coleções
        blogposts_collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
        blogposts_collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)
        
        # Insere em ambas
        blogposts_collection_atlas.insert_one(blog_data)
        blogposts_collection_local.insert_one(blog_data)
        
        elapsed_time = time.perf_counter() - start_time
        return {"data": blog_data}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro interno do servidor"}, 500


def get_blog_post_trivia(tconst):
    """Recupera a postagem do blog para um filme específico"""
    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)
        
        blog_post = blogposts_collection.find_one({"tconst": tconst}, {"_id": 0})
        
        if blog_post:
            return {"data": blog_post}, 200
        else:
            return {"data": "Blog post not found"}, 404
    except Exception as e:
        print(f"Erro: {e}")
        return {"data": "Failed to retrieve blog post"}, 500


def get_blogposts_trivia(filters={}, page=1, page_size=10):
    """Recupera todas as postagens de blog com paginação"""
    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)

        # Garante que os valores são inteiros
        page = int(page)
        page_size = int(page_size)
        
        # Converte filtros de texto para regex case-insensitive
        search_filters = {}
        text_fields = ["tconst", "primaryTitle", "title", "introduction", 
                      "historical_context", "cultural_importance", 
                      "technical_analysis", "conclusion"]
        
        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            else:
                search_filters[key] = value
        
        total_documents = blogposts_collection.count_documents(search_filters)
        skip = (page - 1) * page_size
        
        posts = list(
            blogposts_collection.find(search_filters, {"_id": 0})
            .sort("_id", -1)    
            .skip(skip)
            .limit(page_size)
        )

        return {
            "total_documents": total_documents,
            "entries": posts if posts else []
        }, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {
            "total_documents": 0,
            "entries": []
        }, 500 


def update_blog_post_trivia(tconst, data):
    """Atualiza uma postagem de blog existente"""
    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)
        
        # Verifica se a postagem existe
        existing_post = blogposts_collection.find_one({"tconst": tconst})
        if not existing_post:
            return {"status": 404, "message": "Postagem não encontrada"}, 404
        
        # Atualiza apenas os campos fornecidos
        update_data = {k: v for k, v in data.items() if v is not None}
        
        blogposts_collection.update_one({"tconst": tconst}, {"$set": update_data})
        
        updated_post = blogposts_collection.find_one({"tconst": tconst}, {"_id": 0})
        return {"data": updated_post}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro interno do servidor"}, 500