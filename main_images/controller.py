from flask import request, jsonify
from datetime import datetime
from bson import ObjectId
import boto3
import re
from botocore.exceptions import ClientError
from urllib.parse import quote_plus, quote

from config import get_mongo_collection, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from utils import optimize_image


COLLECTION_NAME = "main-images"
MAIN_PREFIX = "main-images"


def get_next_sequential_id(tconst):
    """Gera o próximo ID sequencial para imagens de um filme específico"""
    collection = get_mongo_collection(COLLECTION_NAME)
    
    # Busca o último ID usado para este tconst
    last_image = collection.find_one(
        {"tconst": tconst}, 
        sort=[("sequential_id", -1)]
    )
    
    if last_image and "sequential_id" in last_image:
        return last_image["sequential_id"] + 1
    else:
        return 1


def save_image_metadata(tconst, filename, sequential_id, subtitle_en="", subtitle_pt=""):
    """Salva metadados da imagem no MongoDB"""
    collection = get_mongo_collection(COLLECTION_NAME)
    
    image_doc = {
        "tconst": tconst,
        "filename": filename,
        "sequential_id": sequential_id,
        "subtitle_en": subtitle_en,
        "subtitle_pt": subtitle_pt,
        "created_at": datetime.utcnow()
    }
    
    try:
        collection.insert_one(image_doc)
        return True
    except Exception as e:
        print(f"Erro ao salvar metadados da imagem: {e}")
        return False


def sanitize_filename(filename):
    """Remove caracteres indesejados e espaços do nome do arquivo."""
    filename = filename.replace(" ", "_")
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    return filename


def upload_image_to_s3(file, bucket_name, tconst, subtitle_en="", subtitle_pt=""):
    """Faz upload de um arquivo para um bucket S3 com ID sequencial"""

    s3_client = boto3.client("s3")

    # Gera o próximo ID sequencial
    sequential_id = get_next_sequential_id(tconst)
    
    # Obtém a extensão do arquivo original
    original_filename = file.filename
    file_extension = ""
    if "." in original_filename:
        file_extension = original_filename.split(".")[-1]
    
    # Cria o nome do arquivo com ID sequencial
    new_filename = f"{sequential_id}.{file_extension}"
    object_name = f"{MAIN_PREFIX}/{tconst}/{new_filename}"

    content_type = "application/octet-stream"
    if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        if file.filename.lower().endswith(".png"):
            content_type = "image/png"
        elif file.filename.lower().endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"

    try:
        # Otimiza a imagem antes do upload (redimensiona e comprime)
        optimized_file = optimize_image(file, max_width=800, quality=85)
        
        # Faz o upload para o S3
        s3_client.upload_fileobj(
            optimized_file, bucket_name, object_name, ExtraArgs={"ContentType": content_type}
        )
        
        # Adiciona tags com as legendas
        if subtitle_en or subtitle_pt:
            sanitized_subtitle_en = sanitize_tag_value(subtitle_en)
            sanitized_subtitle_pt = sanitize_tag_value(subtitle_pt)
            
            s3_client.put_object_tagging(
                Bucket=bucket_name,
                Key=object_name,
                Tagging={
                    "TagSet": [
                        {"Key": "subtitle_en", "Value": sanitized_subtitle_en},
                        {"Key": "subtitle_pt", "Value": sanitized_subtitle_pt},
                    ]
                },
            )
        
        # Salva metadados no MongoDB
        save_image_metadata(tconst, new_filename, sequential_id, subtitle_en, subtitle_pt)
        
        return {
            "message": "Upload realizado com sucesso",
            "object_name": object_name,
            "filename": new_filename,
            "sequential_id": sequential_id,
        }, 200
    except Exception as e:
        print(f"Erro ao fazer upload para S3: {e}")
        return {"status": 500, "message": "Erro ao fazer upload para S3"}, 500


def get_image_url(bucket_name, tconst, filename):
    """Retorna a URL pública direta e as legendas de um arquivo no S3"""
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="us-east-2",
    )

    try:
        object_name = f"{MAIN_PREFIX}/{tconst}/{filename}"

        response = s3_client.get_object_tagging(Bucket=bucket_name, Key=object_name)

        subtitle_en = ""
        subtitle_pt = ""
        for tag in response.get("TagSet", []):
            if tag["Key"] == "subtitle_en":
                subtitle_en = tag["Value"]
            elif tag["Key"] == "subtitle_pt":
                subtitle_pt = tag["Value"]

        url = f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_name}"
        return {"url": url, "filename": filename, "subtitle_en": subtitle_en, "subtitle_pt": subtitle_pt}, 200
    except Exception as e:
        print(f"Erro ao buscar legendas: {e}")
        return {"status": 500, "message": "Erro ao buscar legendas"}, 500


def get_all_image_urls(bucket_name, tconst):
    """Retorna todas as URLs públicas diretas e legendas para imagens associadas a um tconst"""
    collection = get_mongo_collection(COLLECTION_NAME)
    
    try:
        # Busca todas as imagens do tconst no MongoDB, ordenadas por ID sequencial
        images_metadata = collection.find(
            {"tconst": tconst}
        ).sort("sequential_id", 1)
        
        images = []
        for image_doc in images_metadata:
            filename = image_doc["filename"]
            sequential_id = image_doc["sequential_id"]
            subtitle_en = image_doc.get("subtitle_en", "")
            subtitle_pt = image_doc.get("subtitle_pt", "")
            
            url = f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{MAIN_PREFIX}/{tconst}/{filename}"
            
            images.append({
                "url": url,
                "filename": filename,
                "sequential_id": sequential_id,
                "subtitle_en": subtitle_en,
                "subtitle_pt": subtitle_pt,
            })

        return {"images": images}, 200
    except Exception as e:
        print(f"Erro ao listar imagens: {e}")
        return {"status": 500, "message": "Erro ao listar imagens"}, 500


def get_image_by_sequential_id(bucket_name, tconst, sequential_id):
    """Retorna uma imagem específica pelo ID sequencial"""
    collection = get_mongo_collection(COLLECTION_NAME)
    
    try:
        # Busca a imagem pelo tconst e ID sequencial
        image_doc = collection.find_one({
            "tconst": tconst,
            "sequential_id": int(sequential_id)
        })
        
        if not image_doc:
            return {"status": 404, "message": "Imagem não encontrada"}, 404
        
        filename = image_doc["filename"]
        subtitle_en = image_doc.get("subtitle_en", "")
        subtitle_pt = image_doc.get("subtitle_pt", "")
        
        url = f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{MAIN_PREFIX}/{tconst}/{filename}"
        
        return {
            "url": url,
            "filename": filename,
            "sequential_id": sequential_id,
            "subtitle_en": subtitle_en,
            "subtitle_pt": subtitle_pt,
        }, 200
    except Exception as e:
        print(f"Erro ao buscar imagem: {e}")
        return {"status": 500, "message": "Erro ao buscar imagem"}, 500


def delete_image_from_s3(bucket_name, tconst, filename):
    """Deleta uma imagem específica de um bucket S3 e seus metadados"""
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="us-east-2",
    )
    
    collection = get_mongo_collection(COLLECTION_NAME)

    object_name = f"{MAIN_PREFIX}/{tconst}/{filename}"

    try:
        # Remove do S3
        s3_client.delete_object(Bucket=bucket_name, Key=object_name)
        
        # Remove metadados do MongoDB
        collection.delete_one({
            "tconst": tconst,
            "filename": filename
        })
        
        return {"message": f"Imagem '{filename}' deletada com sucesso"}, 200
    except ClientError as e:
        print(f"Erro ao deletar imagem do S3: {e}")
        return {"status": 500, "message": "Erro ao deletar imagem"}, 500
    except Exception as e:
        print(f"Erro ao deletar metadados: {e}")
        return {"status": 500, "message": "Erro ao deletar metadados"}, 500


def sanitize_tag_value(value):
    """Sanitiza o valor da tag para atender aos requisitos do AWS S3"""
    sanitized = re.sub(r"[^\w\s-]", "", value)

    if len(sanitized) > 256:
        words = sanitized[:256].split()
        if len(words) > 1:
            sanitized = " ".join(words[:-1])
        else:
            sanitized = sanitized[:256]

    return sanitized


def update_image_subtitle(bucket_name, tconst, filename, subtitle_en="", subtitle_pt=""):
    """Atualiza as legendas de uma imagem específica usando tags do S3 e MongoDB"""
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="us-east-2",
    )
    
    collection = get_mongo_collection(COLLECTION_NAME)

    try:
        object_name = f"{MAIN_PREFIX}/{tconst}/{filename}"

        sanitized_subtitle_en = sanitize_tag_value(subtitle_en)
        sanitized_subtitle_pt = sanitize_tag_value(subtitle_pt)

        # Atualiza tags no S3
        s3_client.put_object_tagging(
            Bucket=bucket_name,
            Key=object_name,
            Tagging={
                "TagSet": [
                    {"Key": "subtitle_en", "Value": sanitized_subtitle_en},
                    {"Key": "subtitle_pt", "Value": sanitized_subtitle_pt},
                ]
            },
        )
        
        # Atualiza metadados no MongoDB
        collection.update_one(
            {"tconst": tconst, "filename": filename},
            {
                "$set": {
                    "subtitle_en": sanitized_subtitle_en,
                    "subtitle_pt": sanitized_subtitle_pt
                }
            }
        )

        url = f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_name}"
        return {
            "url": url,
            "filename": filename,
            "subtitle_en": sanitized_subtitle_en,
            "subtitle_pt": sanitized_subtitle_pt,
        }, 200

    except Exception as e:
        print(f"Erro ao atualizar legendas: {e}")
        return {"status": 500, "message": "Erro ao atualizar legendas"}, 500


