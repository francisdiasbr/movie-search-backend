from flask import request, jsonify
import os
from config import get_mongo_collection
from .utils import generate_blog_post
import time

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

    # Nova estrutura de dados
    blog_data = {
        "tconst": tconst,
        "primaryTitle": movie.get("primaryTitle"),
        "title": blog_post.get("title"),
        "introduction": blog_post.get("introduction"),
        "historical_context": blog_post.get("historical_context"),
        "cultural_importance": blog_post.get("cultural_importance"),
        "technical_analysis": blog_post.get("technical_analysis"),
        "conclusion": blog_post.get("conclusion"),
        "movieData": {
            "country": movie.get("country"),
            "plot_keywords": movie.get("plot_keywords"),
            "quote": movie.get("quote"),
            # Adicione outros campos do movieData que desejar
        }
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
        blog_posts = list(
            blogposts_collection.find({"tconst": tconst}, {"_id": 0})
        )
        
        if blog_posts:
            return {
                "total_documents": len(blog_posts),
                "entries": blog_posts
            }, 200
        else:
            return {"total_documents": 0, "entries": []}, 404
    except Exception as e:
        print(f"Erro: {e}")
        return {"total_documents": 0, "entries": []}, 500


def get_all_blog_posts(filters={}, page=1, page_size=10):
    """Recupera todas as postagens de blog com paginação"""
    try:
        total_documents = blogposts_collection.count_documents(filters)
        skip = (page - 1) * page_size
        
        items = list(
            blogposts_collection.find(filters)
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )

        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        return {"total_documents": total_documents, "entries": items}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro interno do servidor"}, 500 