from config import get_mongo_collection
from utils import sanitize_filters
from .utils import generate_blog_post
import time
from datetime import datetime

COLLECTION_NAME = "blogposts"


def create_and_save_blog_post(tconst, api_key, model, temperature=0.7, max_tokens=1500):
    """Cria e salva uma postagem de blog para um filme favoritado"""
    print(f"Iniciando a criação do post para o filme: {tconst}")

    try:
        favoritelist_collection = get_mongo_collection("favoritelist")
        print(f"Conectado à coleção de favoritos: {favoritelist_collection}")

        movie = favoritelist_collection.find_one({"tconst": tconst})
        if not movie:
            print("Filme não encontrado nos favoritos.")
            return {"status": 404, "message": "Filme não encontrado nos favoritos"}, 404

        print(f"Filme encontrado: {movie.get('primaryTitle')}")

        blogposts_collection_atlas = get_mongo_collection(
            COLLECTION_NAME, use_atlas=True
        )
        blogposts_collection_local = get_mongo_collection(
            COLLECTION_NAME, use_atlas=False
        )
        print("Conectado às coleções de blogposts (Atlas e Local)")

        existing_post_atlas = blogposts_collection_atlas.find_one({"tconst": tconst})
        existing_post_local = blogposts_collection_local.find_one({"tconst": tconst})

        if existing_post_atlas or existing_post_local:
            print("Já existe uma resenha para este filme.")
            return {
                "status": 400,
                "message": "Já existe uma resenha para este filme",
            }, 400

        print("Nenhuma resenha existente encontrada. Gerando nova postagem de blog...")

        # Inicia o cronômetro
        start_time = time.perf_counter()

        # Chama a função para gerar a postagem de blog
        blog_post_response = generate_blog_post(
            api_key, movie, model, temperature, max_tokens
        )
        print(f"Resposta da geração do blog post: {blog_post_response}")

        if blog_post_response[1] != 200:
            print("Erro ao gerar postagem do blog.")
            return {"status": 500, "message": "Erro ao gerar postagem do blog"}, 500

        blog_post = blog_post_response[0].get("data")
        print(f"Blog post gerado: {blog_post}")

        creation_timestamp = datetime.now().isoformat()

        # Obtém as referências do filme favorito
        references = movie.get("references", [])

        # Monta o objeto de dados do blog
        blog_data = {
            "data": {
                "tconst": tconst,
                "primaryTitle": movie.get("primaryTitle"),
                "content": blog_post["content"],
                "original_movie_soundtrack": blog_post.get("original_movie_soundtrack"),
                "created_at": creation_timestamp,
                "references": references,
                "soundtrack_video_url": blog_post.get("soundtrack_video_url"),
                "spotify_album_url": blog_post.get("spotify_album_url"),
                "isAiGenerated": True,
            }
        }

        print(f"\nDados do blog post preparados. Spotify URL: {blog_data['data'].get('spotify_album_url')}")

        # Remove _id antes de inserir
        blog_data["data"].pop("_id", None)

        # Insere nos bancos de dados
        atlas_result = blogposts_collection_atlas.insert_one(blog_data["data"])
        local_result = blogposts_collection_local.insert_one(blog_data["data"])

        # Adiciona o _id apenas na resposta
        blog_data["data"]["_id"] = str(atlas_result.inserted_id)

        print(f"\nBlog post salvo com sucesso. Resposta final: {blog_data}")
        return blog_data, 200

    except Exception as e:
        print(f"Erro inesperado: {e}")
        return {"status": 500, "message": str(e)}, 500


def get_blog_post(tconst):
    """Recupera a postagem do blog para um filme específico"""
    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)

        # Adiciona spotify_album_url aos campos a serem retornados
        projection = {
            "_id": 0,
            "spotify_album_url": 1,
            "tconst": 1,
            "primaryTitle": 1,
            "content": 1,
            "original_movie_soundtrack": 1,
            "created_at": 1,
            "references": 1,
            "soundtrack_video_url": 1,
            "isAiGenerated": 1
        }

        blog_post = blogposts_collection.find_one({"tconst": tconst}, projection)

        if blog_post:
            if "content" not in blog_post:
                blog_post["content"] = {
                    "pt": {
                        "title": blog_post.get("title", ""),
                        "introduction": blog_post.get("introduction", ""),
                        "plot_summary": blog_post.get("plot_summary", ""),
                        "acting_analysis": blog_post.get("acting_analysis", ""),
                        "personal_impressions": blog_post.get("personal_impressions", ""),
                        "recommendation": blog_post.get("recommendation", "")
                    },
                    "en": {
                        "title": blog_post.get("title_en", ""),
                        "introduction": blog_post.get("introduction_en", ""),
                        "plot_summary": blog_post.get("plot_summary_en", ""),
                        "acting_analysis": blog_post.get("acting_analysis_en", ""),
                        "personal_impressions": blog_post.get("personal_impressions_en", ""),
                        "recommendation": blog_post.get("recommendation_en", "")
                    }
                }

                # Remove campos antigos se existirem
                fields_to_remove = [
                    "title",
                    "introduction",
                    "plot_summary",
                    "acting_analysis",
                    "personal_impressions",
                    "recommendation",
                    "title_en",
                    "introduction_en",
                    "plot_summary_en",
                    "acting_analysis_en",
                    "personal_impressions_en",
                    "recommendation_en"
                ]
                for field in fields_to_remove:
                    blog_post.pop(field, None)

            return {"data": blog_post}, 200
        else:
            return {"message": "Blog post not found"}, 404
    except Exception as e:
        print(f"Erro: {e}")
        return {"message": "Failed to retrieve blog post"}, 500


def get_blogposts(filters={}, page=1, page_size=10):
    """Recupera todas as postagens de blog com paginação"""
    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)

        page = int(page)
        page_size = int(page_size)

        search_filters = {}
        text_fields = ["tconst", "primaryTitle"]
        content_fields = [
            "title",
            "introduction",
            "stars_and_characters",
            "historical_context",
            "cultural_importance",
            "technical_analysis",
            "conclusion",
        ]

        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            elif key in content_fields and isinstance(value, str):
                search_filters["$or"] = [
                    {f"content.pt.{key}": {"$regex": value, "$options": "i"}},
                    {f"content.en.{key}": {"$regex": value, "$options": "i"}},
                ]
            else:
                search_filters[key] = value

        # Sanitiza os filtros para garantir que valores $regex sejam strings
        search_filters = sanitize_filters(search_filters)

        total_documents = blogposts_collection.count_documents(search_filters)
        skip = (page - 1) * page_size

        # Adiciona spotify_album_url aos campos a serem retornados
        projection = {
            "_id": 0,
            "spotify_album_url": 1,
            "tconst": 1,
            "primaryTitle": 1,
            "content": 1,
            "original_movie_soundtrack": 1,
            "created_at": 1,
            "references": 1,
            "soundtrack_video_url": 1,
            "isAiGenerated": 1
        }

        posts = list(
            blogposts_collection.find(search_filters, projection)
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )

        for post in posts:
            if "content" not in post:
                post["content"] = {
                    "pt": {
                        "title": post.pop("title", ""),
                        "introduction": post.pop("introduction", ""),
                        "stars_and_characters": post.pop("stars_and_characters", ""),
                        "historical_context": post.pop("historical_context", ""),
                        "cultural_importance": post.pop("cultural_importance", ""),
                        "technical_analysis": post.pop("technical_analysis", ""),
                        "conclusion": post.pop("conclusion", ""),
                    },
                    "en": {
                        "title": post.pop("title_en", ""),
                        "introduction": post.pop("introduction_en", ""),
                        "stars_and_characters": post.pop("stars_and_characters_en", ""),
                        "historical_context": post.pop("historical_context_en", ""),
                        "cultural_importance": post.pop("cultural_importance_en", ""),
                        "technical_analysis": post.pop("technical_analysis_en", ""),
                        "conclusion": post.pop("conclusion_en", ""),
                    },
                }

        return {
            "total_documents": total_documents,
            "entries": posts if posts else [],
        }, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"total_documents": 0, "entries": []}, 500


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
        if "references" in update_data and not isinstance(
            update_data["references"], list
        ):
            return {
                "status": 400,
                "message": "A propriedade 'references' deve ser uma lista de strings",
            }, 400

        blogposts_collection.update_one({"tconst": tconst}, {"$set": update_data})

        updated_post = blogposts_collection.find_one({"tconst": tconst}, {"_id": 0})
        return {"data": updated_post}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro interno do servidor"}, 500


def delete_blog_post(tconst):
    """Deleta uma postagem de blog específica usando o tconst"""
    try:
        blogposts_collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
        blogposts_collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)

        # Verifica se a postagem existe
        existing_post_atlas = blogposts_collection_atlas.find_one({"tconst": tconst})
        existing_post_local = blogposts_collection_local.find_one({"tconst": tconst})

        if not existing_post_atlas and not existing_post_local:
            return {"data": f"review for movie {tconst} not found"}

        # Deleta a postagem em ambos os bancos de dados
        result_atlas = blogposts_collection_atlas.delete_one({"tconst": tconst})
        result_local = blogposts_collection_local.delete_one({"tconst": tconst})

        if result_atlas.deleted_count > 0 or result_local.deleted_count > 0:
            return {"data": f"review for movie {tconst} deleted"}
        else:
            return {"data": f"error deleting review for movie {tconst}"}

    except Exception as e:
        print(f"Erro ao deletar postagem: {e}")
        return {"data": f"error deleting review for movie {tconst}: {str(e)}"}


def get_soundtrack_by_title(title):
    """Busca a trilha sonora de um filme pelo título"""
    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)
        
        # Busca o filme pelo título (case insensitive e correspondência parcial)
        movie = blogposts_collection.find_one(
            {"primaryTitle": {"$regex": title, "$options": "i"}}
        )
        
        if not movie:
            return {"data": f"movie with title '{title}' not found"}
            
        soundtrack_data = {
            "tconst": movie.get("tconst"),
            "title": movie.get("primaryTitle"),
            "original_movie_soundtrack": movie.get("original_movie_soundtrack"),
            "soundtrack_video_url": movie.get("soundtrack_video_url"),
            "spotify_album_url": movie.get("spotify_album_url", "No album found")
        }
        
        return {"data": soundtrack_data}
        
    except Exception as e:
        print(f"Erro ao buscar trilha sonora: {e}")
        return {"data": f"error getting soundtrack for movie '{title}': {str(e)}"}
