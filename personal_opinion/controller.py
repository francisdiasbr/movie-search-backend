from flask import request, jsonify
from datetime import datetime
from bson import ObjectId
import boto3
import re
from botocore.exceptions import ClientError
from urllib.parse import quote_plus, quote

from config import get_mongo_collection, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


COLLECTION_NAME = "personal_opinions"


def insert_personal_opinion(tconst, opinion=None, enjoying_1=None, enjoying_2=None):
    """Insere uma nova opinião pessoal no banco de dados"""
    try:
        collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
        collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)
        
        existing_opinion_atlas = collection_atlas.find_one({"tconst": tconst})
        existing_opinion_local = collection_local.find_one({"tconst": tconst})
        
        if existing_opinion_atlas or existing_opinion_local:
            return {"status": 400, "message": "Já existe uma opinião para este filme"}, 400
        
        # Define valores padrão
        if opinion is None:
            opinion = "Este filme é uma obra-prima da história do Cinema"
        if enjoying_1 is None:
            enjoying_1 = "sim"
        if enjoying_2 is None:
            enjoying_2 = "sim"
        
        personal_opinion_data = {
            "tconst": tconst,
            "opinion": opinion,
            "enjoying_1": enjoying_1,
            "enjoying_2": enjoying_2,
            "created_at": datetime.now().isoformat()
        }
        
        # Insere em ambas as coleções
        result_atlas = collection_atlas.insert_one(personal_opinion_data)
        result_local = collection_local.insert_one(personal_opinion_data)
        
        personal_opinion_data["_id"] = str(result_atlas.inserted_id)
        return {"data": personal_opinion_data}, 201
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao inserir opinião pessoal"}, 500


def get_personal_opinion(tconst):
    """Recupera a primeira opinião pessoal para um filme específico"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        opinion = personal_opinions_collection.find_one({"tconst": tconst})
        
        if opinion:
            opinion["_id"] = str(opinion["_id"])
            return {"data": opinion}, 200
        else:
            return {"status": 404, "message": "Opinião não encontrada"}, 404
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao recuperar opinião pessoal"}, 500


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
        text_fields = ["tconst", "opinion", "enjoying_1", "enjoying_2"]
        
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


def update_personal_opinion(tconst, opinion=None, enjoying_1=None, enjoying_2=None):
    """Atualiza uma opinião pessoal existente"""
    try:
        collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
        collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)
        
        # Verifica se a opinião existe
        existing_opinion = collection_atlas.find_one({"tconst": tconst})
        if not existing_opinion:
            return {"status": 404, "message": "Não existe opinião cadastrada para este filme"}, 404
        
        # Prepara os dados para atualização
        update_data = {}
        if opinion is not None:
            update_data["opinion"] = opinion
        if enjoying_1 is not None:
            update_data["enjoying_1"] = enjoying_1
        if enjoying_2 is not None:
            update_data["enjoying_2"] = enjoying_2
        
        if not update_data:
            return {"status": 400, "message": "Nenhum dado fornecido para atualização"}, 400
            
        update_data["updated_at"] = datetime.now().isoformat()
        
        # Atualiza em ambas as coleções
        collection_atlas.update_one(
            {"tconst": tconst},
            {"$set": update_data}
        )
        collection_local.update_one(
            {"tconst": tconst},
            {"$set": update_data}
        )
        
        # Retorna a opinião atualizada
        updated_opinion = collection_atlas.find_one({"tconst": tconst})
        updated_opinion["_id"] = str(updated_opinion["_id"])
        return {"data": updated_opinion, "message": "Opinião atualizada com sucesso"}, 200
            
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao atualizar opinião pessoal"}, 500