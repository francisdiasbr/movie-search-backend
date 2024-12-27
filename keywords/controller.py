from flask import request, jsonify
from config import get_mongo_collection

COLLECTION_NAME = "favorites_keywords"


def add_keyword(keyword):
    """Adiciona uma palavra-chave aos favoritos"""
    if not keyword:
        return {"data": "Keyword is required"}, 400

    collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
    collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)

    # Verifica se a palavra-chave já está na lista de favoritos
    existing_keyword_atlas = collection_atlas.find_one({"keyword": keyword})
    existing_keyword_local = collection_local.find_one({"keyword": keyword})
    
    if existing_keyword_atlas or existing_keyword_local:
        return {"data": "Keyword already listed"}, 409

    try:
        # Insere em ambas as coleções
        result_atlas = collection_atlas.insert_one({"keyword": keyword})
        result_local = collection_local.insert_one({"keyword": keyword})
        
        inserted_keyword = collection_atlas.find_one({"_id": result_atlas.inserted_id})
        if inserted_keyword:
            return {
                "data": {
                    "_id": str(inserted_keyword["_id"]),
                    "keyword": inserted_keyword["keyword"],
                }
            }, 201
        return {"data": "Failed to retrieve inserted keyword"}, 500
    except Exception as e:
        print(f"Error: {e}")
        return {"data": "Failed to add keyword"}, 500


def get_favorited_keywords():
    """Recupera todas as palavras-chave favoritas"""
    collection = get_mongo_collection(COLLECTION_NAME)
    try:
        keywords = list(collection.find({}, {"_id": 1, "keyword": 1}))
        # Converte ObjectId para string
        for keyword in keywords:
            keyword["_id"] = str(keyword["_id"])
        return {"data": keywords}, 200
    except Exception as e:
        print(f"Error: {e}")
        return {"data": "Failed to retrieve keywords"}, 500


def delete_favorited_keyword(keyword):
    """Remove uma palavra-chave dos favoritos"""
    if not keyword:
        return {"data": "Keyword is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    try:
        result = collection.delete_one({"keyword": keyword})
        if result.deleted_count:
            return {"data": "Keyword deleted successfully"}, 200
        return {"data": "Keyword not found"}, 404
    except Exception as e:
        print(f"Error: {e}")
        return {"data": "Failed to delete keyword"}, 500
