from flask import jsonify
from openai import OpenAI
import os

from config import get_mongo_collection
from utils import sanitize_movie_data

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

blogposts_collection = get_mongo_collection("blogposts")

def generate_blog_post(movie_data):
    """Gera uma postagem de blog baseada nos dados do filme"""
    
    messages = [
        {
            "role": "system",
            "content": "Você é um blogueiro especializado em cinema que escreve em português. Seu estilo é envolvente e informativo.",
        },
        {
            "role": "user",
            "content": f"""
            Crie uma postagem de blog sobre o filme usando estas informações:
            
            Título: {movie_data.get('primaryTitle')}
            Ano: {movie_data.get('startYear')}
            Gêneros: {movie_data.get('genres', [])}
            Diretor: {movie_data.get('directors', [])}
            Elenco: {movie_data.get('actors', [])}
            
            A postagem deve incluir:
            1. Um título criativo
            2. Introdução cativante
            3. Análise do contexto histórico
            4. Discussão sobre a importância cultural do filme
            5. Análise dos elementos técnicos e artísticos
            6. Conclusão que convide à reflexão
            """,
        },
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4", 
            messages=messages, 
            max_tokens=1500, 
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro ao gerar blog post: {e}")
        return None

def create_and_save_blog_post(tconst):
    """Cria e salva uma postagem de blog para um filme favoritado"""
    favoritelist_collection = get_mongo_collection("favoritelist")
    
    movie = favoritelist_collection.find_one({"tconst": tconst})
    if not movie:
        return {"status": 404, "message": "Filme não encontrado nos favoritos"}, 404

    blog_post = generate_blog_post(movie)
    if not blog_post:
        return {"status": 500, "message": "Erro ao gerar postagem do blog"}, 500

    blog_data = {
        "tconst": tconst,
        "primaryTitle": movie.get("primaryTitle"),
        "blogPost": blog_post,
        "movieData": movie
    }

    try:
        blogposts_collection.insert_one(blog_data)
        return blog_data, 200
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