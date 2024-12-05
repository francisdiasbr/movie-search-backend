from flask import request, jsonify
from config import get_mongo_collection

COLLECTION_NAME = "favorites_keywords"

def add_keyword(keyword):
    """Adiciona uma palavra-chave aos favoritos"""
    if not keyword:
        return {"data": "Keyword is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    # Verifica se a palavra-chave já está na lista de favoritos
    existing_keyword = collection.find_one({"keyword": keyword})
    if existing_keyword:
        return {"data": "Keyword already listed"}, 409

    # Insere a nova palavra-chave
    try:
        result = collection.insert_one({"keyword": keyword})
        inserted_keyword = collection.find_one({"_id": result.inserted_id})
        if inserted_keyword:
            return {
                "data": {
                    "_id": str(inserted_keyword["_id"]),
                    "keyword": inserted_keyword["keyword"]
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