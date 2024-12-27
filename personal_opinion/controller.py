from flask import request, jsonify
from datetime import datetime
from bson import ObjectId
import boto3
import re
from botocore.exceptions import ClientError
from urllib.parse import quote_plus, quote

from config import get_mongo_collection, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


COLLECTION_NAME = "personal_opinions"


def insert_personal_opinion(tconst, opinion=None, rate=None):
    """Insere uma nova opinião pessoal no banco de dados"""
    try:
        collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
        collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)
        
        # Verifica em ambas as coleções
        existing_opinion_atlas = collection_atlas.find_one({"tconst": tconst})
        existing_opinion_local = collection_local.find_one({"tconst": tconst})
        
        if existing_opinion_atlas or existing_opinion_local:
            return {"status": 400, "message": "Já existe uma opinião para este filme"}, 400
        
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


def sanitize_filename(filename):
    """Remove caracteres indesejados do nome do arquivo."""
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    return filename


def upload_image_to_s3(file, bucket_name, object_name=None):
    """Faz upload de um arquivo para um bucket S3"""
    
    s3_client = boto3.client('s3')
    
    if object_name is None:
        object_name = sanitize_filename(file.filename)
    
    content_type = 'application/octet-stream'
    if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        if file.filename.lower().endswith('.png'):
            content_type = 'image/png'
        elif file.filename.lower().endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
    
    try:
        s3_client.upload_fileobj(
            file,
            bucket_name,
            object_name,
            ExtraArgs={'ContentType': content_type}
        )
        return {"message": "Upload realizado com sucesso", "object_name": object_name}, 200
    except Exception as e:
        print(f"Erro ao fazer upload para S3: {e}")
        return {"status": 500, "message": "Erro ao fazer upload para S3"}, 500


def get_image_url(bucket_name, tconst, filename, expiration=3600):
    """Gera uma URL pré-assinada para acessar um arquivo no S3"""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name='us-east-2'
    )
    
    object_name = f"{tconst}/{quote(filename)}"
    
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name, 'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        print(f"Erro ao gerar URL pré-assinada: {e}")
        return {"status": 500, "message": "Erro ao gerar URL pré-assinada"}, 500

    return {"url": response}, 200


def get_public_image_url(bucket_name, tconst, filename):
    """Retorna a URL pública direta para acessar um arquivo no S3"""

    object_name = f"{tconst}/{filename}"
    url = f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_name}"
    return {"url": url}, 200


def get_all_image_urls(bucket_name, tconst):
    """Retorna todas as URLs públicas diretas e nomes de arquivos para imagens associadas a um tconst"""

    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name='us-east-2'
    )
    
    try:
        # Lista todos os objetos no bucket que começam com o prefixo tconst
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"{tconst}/")
        images = []
        for obj in response.get('Contents', []):
            object_name = obj['Key']
            filename = object_name.split('/')[-1]
            
            url = f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_name}"
            images.append({
                "url": url,
                "filename": filename,
                "last_modified": obj['LastModified']
            })
        
        
        images.sort(key=lambda x: x['last_modified'])
        
        for image in images:
            del image['last_modified']
        
        return {"images": images}, 200
    except ClientError as e:
        print(f"Erro ao listar objetos no S3: {e}")
        return {"status": 500, "message": "Erro ao listar imagens"}, 500


def delete_image_from_s3(bucket_name, tconst, filename):
    """Deleta uma imagem específica de um bucket S3"""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name='us-east-2'
    )
    
    object_name = f"{tconst}/{filename}"
    
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=object_name)
        return {"message": f"Imagem '{filename}' deletada com sucesso"}, 200
    except ClientError as e:
        print(f"Erro ao deletar imagem do S3: {e}")
        return {"status": 500, "message": "Erro ao deletar imagem"}, 500

