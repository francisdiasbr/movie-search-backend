from flask import request, jsonify
import os
from config import get_mongo_collection
from .utils import generate_blog_post
from favorites.scrapper import get_movie_poster
import time
from datetime import datetime
from .scraper import get_google_images  # Importa a função de scraping

COLLECTION_NAME = "blogposts"

def create_and_save_blog_post(tconst, api_key, model, temperature=0.7, max_tokens=1500):
    """Cria e salva uma postagem de blog para um filme favoritado"""
    start_time = time.perf_counter()

    favoritelist_collection = get_mongo_collection("favoritelist")
    
    movie = favoritelist_collection.find_one({"tconst": tconst})
    if not movie:
        return {"status": 404, "message": "Filme não encontrado nos favoritos"}, 404

    # Chama a função para gerar a postagem de blog
    blog_post_response = generate_blog_post(api_key, movie, model, temperature, max_tokens)

    # Verifica se a geração da postagem foi bem-sucedida
    if blog_post_response[1] != 200:
        return {"status": 500, "message": "Erro ao gerar postagem do blog"}, 500

    blog_post = blog_post_response[0].get("data")

    # Obtém a URL do pôster do filme
    poster_url = get_movie_poster(tconst)

    print(f"Poster URL: {poster_url}")

    creation_timestamp = datetime.now().isoformat()
    # Concatena o título principal com "movie scenes"
    query = f"{movie.get('primaryTitle')} movie scenes"

    # Obtém as primeiras 5 imagens do Google Imagens usando a nova consulta
    images = get_google_images(query, num_images=5)

    # Nova estrutura de dados
    blog_data = {
        "tconst": tconst,
        "primaryTitle": movie.get("primaryTitle"),
        "title": blog_post.get("title"),
        "introduction": blog_post.get("introduction"),
        "stars_and_characters": blog_post.get("stars_and_characters"),
        "historical_context": blog_post.get("historical_context"),
        "cultural_importance": blog_post.get("cultural_importance"),
        "technical_analysis": blog_post.get("technical_analysis"),
        "conclusion": blog_post.get("conclusion"),
        "original_movie_soundtrack": blog_post.get("original_movie_soundtrack"),
        "poster_url": poster_url,
        "created_at": creation_timestamp,
        "references": [],
        "soundtrack_video_url": blog_post.get("soundtrack_video_url"),
        "images": images,  # Adiciona a lista de URLs das imagens
    }

    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)
        blogposts_collection.insert_one(blog_data)
        elapsed_time = time.perf_counter() - start_time
        print(f"Tempo para criar e salvar postagem de blog: {elapsed_time:.6f} segundos")
        return {"data": blog_data}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro interno do servidor"}, 500


def get_blog_post(tconst):
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


def get_blogposts(filters={}, page=1, page_size=10):
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


def update_blog_post(tconst, data):
    """Atualiza uma postagem de blog existente"""
    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)
        
        # Verifica se a postagem existe
        existing_post = blogposts_collection.find_one({"tconst": tconst})
        if not existing_post:
            return {"status": 404, "message": "Postagem não encontrada"}, 404
        
        # Atualiza apenas os campos fornecidos
        update_data = {k: v for k, v in data.items() if v is not None}
        
        # Verifica se "references" é uma lista de strings
        if "references" in update_data and not isinstance(update_data["references"], list):
            return {"status": 400, "message": "A propriedade 'references' deve ser uma lista de strings"}, 400
        
        blogposts_collection.update_one({"tconst": tconst}, {"$set": update_data})
        
        updated_post = blogposts_collection.find_one({"tconst": tconst}, {"_id": 0})
        return {"data": updated_post}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro interno do servidor"}, 500