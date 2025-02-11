from flask import jsonify, request
import json
from datetime import datetime

from config import get_mongo_collection
from utils import sanitize_movie_data
from bson import ObjectId

authoralreviewslist_collection = get_mongo_collection("authoralreviewslist")
favoritelist_collection = get_mongo_collection("favoritelist")

COLLECTION_NAME = "authoralreviewslist"

# Cria e salva uma resenha para um filme
def create_and_save_movie_review(tconst):
    """Cria e salva uma resenha para um filme"""
    print(f"Iniciando a criação da resenha para o filme: {tconst}")

    try:
        favoritelist_collection = get_mongo_collection("favoritelist")
        print(f"Conectado à coleção de favoritos: {favoritelist_collection}")

        movie = favoritelist_collection.find_one({"tconst": tconst})

        if not movie:
            print("Filme não encontrado nos favoritos.")
            return {"status": 404, "message": "Filme não encontrado nos favoritos"}, 404

        # print(f"Filme encontrado: {movie.get('primaryTitle')}")

        authoralreviewslist_collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
        authoralreviewslist_collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)
        # print("Conectado às coleções de blogposts (Atlas e Local)")

        existing_post_atlas = authoralreviewslist_collection_atlas.find_one({"tconst": tconst})
        existing_post_local = authoralreviewslist_collection_local.find_one({"tconst": tconst})

        if existing_post_atlas or existing_post_local:
            print("Já existe uma resenha para este filme.")
            return {"status": 400, "message": "Já existe uma resenha para este filme"}, 400

        review_data = request.json
        # print("Dados recebidos:", json.dumps(review_data, indent=2))  # Debug

        review_content = review_data.get("content", {})
        # print("Conteúdo da review:", json.dumps(review_content, indent=2))  # Debug

        primaryTitle = movie.get("primaryTitle", "")

        creation_timestamp = datetime.now().isoformat()
        
        review_document = {
            "tconst": tconst,
            "primaryTitle": primaryTitle,
            "content": review_content,
            "created_at": creation_timestamp,
            "isAiGenerated": review_data.get("isAiGenerated", False),
            "references": review_data.get("references", []),
            "images": review_data.get("images", [])
        }

        # print("Documento a ser salvo:", json.dumps(review_document, indent=2))  # Debug

        atlas_result = authoralreviewslist_collection_atlas.insert_one(review_document)
        authoralreviewslist_collection_local.insert_one(review_document)
        
        # Convertendo o ObjectId para string antes de retornar
        review_document['_id'] = str(atlas_result.inserted_id)
        
        return {"data": review_document}, 200

    except Exception as e:
        print(f"Erro inesperado: {e}")
        return {"status": 500, "message": str(e)}, 500


# Obtém uma resenha específica
def get_movie_review(tconst):
    try:
        # Buscar todas as reviews para o tconst específico
        movie_reviews = list(
            authoralreviewslist_collection.find(
                {"tconst": tconst},
                {
                    "_id": 1,
                    "tconst": 1,
                    "primaryTitle": 1,
                    "content": 1,
                    "created_at": 1,
                    "isAiGenerated": 1,
                    "references": 1,
                    "images": 1
                }
            )
        )

        # Converter ObjectId para string em cada review
        for review in movie_reviews:
            review["_id"] = str(review["_id"])

        if movie_reviews:
            return {
                "total_documents": len(movie_reviews),
                "entries": movie_reviews,
            }, 200
        else:
            return {"message": "No reviews found for this movie"}, 404

    except Exception as e:
        print(f"Error: {e}")
        return {"message": "Internal server error"}, 500


# Atualiza uma resenha existente
def edit_movie_review(tconst, request_data):
    """Atualiza uma resenha específica"""
    try:
        # Verifica se a review existe usando tconst
        existing_review = authoralreviewslist_collection.find_one({"tconst": tconst})

        if not existing_review:
            return {"message": "Review not found"}, 404

        # Campos permitidos para atualização
        update_data = {
            "content": request_data.get("content"),
            "references": request_data.get("references"),
            "images": request_data.get("images")
        }
        
        # Remove campos None do update_data
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            return {"message": "No valid fields to update"}, 400

        # Atualiza o documento específico
        result = authoralreviewslist_collection.update_one(
            {"tconst": tconst},
            {"$set": update_data}
        )

        if result.modified_count == 1:
            # Busca a review atualizada para retornar
            updated_review = authoralreviewslist_collection.find_one(
                {"tconst": tconst},
                {"_id": 0}  # Exclui o _id do resultado
            )
            return {"data": updated_review}, 200
        else:
            return {"message": "No changes were made"}, 400

    except Exception as e:
        print(f"Error updating review: {e}")
        return {"message": "Failed to update review"}, 500


# Remove uma resenha da base
def delete_movie_review(tconst):
    """Remove uma resenha da base usando apenas o tconst"""
    try:
        authoralreviewslist_collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
        authoralreviewslist_collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)

        result_atlas = authoralreviewslist_collection_atlas.delete_one({"tconst": tconst})
        result_local = authoralreviewslist_collection_local.delete_one({"tconst": tconst})

        if result_atlas.deleted_count == 1 or result_local.deleted_count == 1:
            return {"message": "Review deleted successfully"}, 200
        else:
            return {"status": 404, "message": "Review not found"}, 404
    except Exception as e:
        print(f"Error deleting review: {e}")
        return {"status": 500, "message": "Failed to delete review"}, 500


# Recupera as resenhas criadas
def get_created_reviews(filters={}, sorters=["_id", -1], page=1, page_size=10):
    collection = authoralreviewslist_collection

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

        return {"total_documents": total_documents, "entries": items}, 200
    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Internal server error"}, 500
