from flask import request, jsonify
from config import get_mongo_collection
from datetime import datetime
from bson import ObjectId

COLLECTION_NAME = "personal_opinions"

def insert_personal_opinion(tconst, opinion, rate):
    """Insere uma nova opinião pessoal no banco de dados"""
    try:
        personal_opinion_data = {
            "tconst": tconst,
            "opinion": opinion,
            "rate": rate,
            "created_at": datetime.now().isoformat()
        }
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        result = personal_opinions_collection.insert_one(personal_opinion_data)
        
        # Adiciona o ID do documento ao dicionário de dados, convertendo para string
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
        
        # Converte ObjectId para string
        for opinion in opinions:
            opinion["_id"] = str(opinion["_id"])
        
        return {"data": opinions}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao recuperar opiniões pessoais"}, 500

