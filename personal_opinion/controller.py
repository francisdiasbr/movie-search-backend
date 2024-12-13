from flask import request, jsonify
from config import get_mongo_collection
from datetime import datetime
from bson import ObjectId

COLLECTION_NAME = "personal_opinions"

def insert_personal_opinion(tconst, opinion=None, rate=None):
    """Insere uma nova opinião pessoal no banco de dados"""
    try:
        # Define valores padrão
        if opinion is None:
            opinion = "Este filme é uma obra-prima da história do Cinema"
        if rate is None:
            rate = "10.0"
        
        personal_opinion_data = {
            "tconst": tconst,
            "opinion": opinion,
            "rate": rate,
            "created_at": datetime.now().isoformat()
        }
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        result = personal_opinions_collection.insert_one(personal_opinion_data)
        personal_opinion_data["_id"] = str(result.inserted_id)
        return {"data": personal_opinion_data}, 201
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao inserir opinião pessoal"}, 500

def get_personal_opinions(tconst):
    """Recupera todas as opiniões pessoais para um filme específico"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        opinions = list(personal_opinions_collection.find({"tconst": tconst}))
        
        for opinion in opinions:
            opinion["_id"] = str(opinion["_id"])
        
        return {"data": opinions}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao recuperar opiniões pessoais"}, 500

def get_all_personal_opinions():
    """Recupera todas as opiniões pessoais"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        opinions = list(personal_opinions_collection.find({}))
        
        for opinion in opinions:
            opinion["_id"] = str(opinion["_id"])
        
        return {"data": opinions}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao recuperar opiniões pessoais"}, 500

def delete_personal_opinion(tconst, opinion_id):
    """Deleta uma opinião pessoal específica"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        result = personal_opinions_collection.delete_one({"tconst": tconst, "_id": ObjectId(opinion_id)})
        
        if result.deleted_count == 1:
            return {"message": "Opinião deletada com sucesso"}, 200
        else:
            return {"message": "Opinião não encontrada"}, 404
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao deletar opinião pessoal"}, 500

def search_personal_opinions(filters, page=1, page_size=10):
    """Pesquisa opiniões pessoais com base em filtros e paginação"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        
        search_filters = {}
        text_fields = ["tconst", "opinion", "rate"]
        
        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            else:
                search_filters[key] = value
        
        total_documents = personal_opinions_collection.count_documents(search_filters)
        skip = (page - 1) * page_size
        
        opinions = list(
            personal_opinions_collection.find(search_filters)
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )
        
        for opinion in opinions:
            opinion["_id"] = str(opinion["_id"])
        
        return {
            "total_documents": total_documents,
            "entries": opinions
        }, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao pesquisar opiniões pessoais"}, 500

