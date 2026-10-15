import logging

from datetime import datetime
import boto3
import re
from botocore.exceptions import ClientError

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    MAIN_IMAGES_COLLECTION,
    S3_BUCKET,
    get_mongo_collection,
)
from utils import error, optimize_image

logger = logging.getLogger(__name__)


MAIN_PREFIX = "main-images"


def images():
    return get_mongo_collection(MAIN_IMAGES_COLLECTION)


class StorageUnavailable(Exception):
    """Raised when the AWS credentials are missing. app.py turns it into a 503."""


def s3_client():
    """S3 client with explicit credentials; the same for upload and delete."""
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise StorageUnavailable("Credenciais AWS não configuradas")
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def public_url(tconst, filename):
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{MAIN_PREFIX}/{tconst}/{filename}"


def get_next_sequential_id(tconst):
    """Next sequential id for the images of a movie (1 when it has none)."""
    last_image = images().find_one({"tconst": tconst}, sort=[("sequential_id", -1)])
    return (last_image or {}).get("sequential_id", 0) + 1


def upload_image_to_s3(file, tconst, subtitle_en="", subtitle_pt=""):
    """Faz upload de um arquivo para o bucket S3 com ID sequencial"""

    s3 = s3_client()

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
        s3.upload_fileobj(
            optimized_file, S3_BUCKET, object_name, ExtraArgs={"ContentType": content_type}
        )
        
        # Adiciona tags com as legendas
        if subtitle_en or subtitle_pt:
            sanitized_subtitle_en = sanitize_tag_value(subtitle_en)
            sanitized_subtitle_pt = sanitize_tag_value(subtitle_pt)
            
            s3.put_object_tagging(
                Bucket=S3_BUCKET,
                Key=object_name,
                Tagging={
                    "TagSet": [
                        {"Key": "subtitle_en", "Value": sanitized_subtitle_en},
                        {"Key": "subtitle_pt", "Value": sanitized_subtitle_pt},
                    ]
                },
            )
        
        images().insert_one(
            {
                "tconst": tconst,
                "filename": new_filename,
                "sequential_id": sequential_id,
                "subtitle_en": subtitle_en,
                "subtitle_pt": subtitle_pt,
                "created_at": datetime.utcnow(),
            }
        )
        
        return {
            "message": "Upload realizado com sucesso",
            "object_name": object_name,
            "filename": new_filename,
            "sequential_id": sequential_id,
        }, 200
    except Exception as e:
        logger.error("Erro ao fazer upload para S3: %s", e)
        return error("Erro ao fazer upload para S3", 500)


def get_all_image_urls(tconst):
    """Retorna todas as URLs públicas diretas e legendas para imagens associadas a um tconst"""
    metadata = images().find({"tconst": tconst}).sort("sequential_id", 1)
    return {
        "images": [
            {
                "url": public_url(tconst, doc["filename"]),
                "filename": doc["filename"],
                "sequential_id": doc["sequential_id"],
                "subtitle_en": doc.get("subtitle_en", ""),
                "subtitle_pt": doc.get("subtitle_pt", ""),
            }
            for doc in metadata
        ]
    }, 200


def delete_image_from_s3(tconst, filename):
    """Deleta uma imagem específica do bucket S3 e seus metadados"""
    object_name = f"{MAIN_PREFIX}/{tconst}/{filename}"
    try:
        s3_client().delete_object(Bucket=S3_BUCKET, Key=object_name)
    except ClientError as e:
        logger.error("Could not delete %s from S3: %s", object_name, e)
        return error("Erro ao deletar imagem", 500)

    images().delete_one({"tconst": tconst, "filename": filename})
    return {"message": f"Imagem '{filename}' deletada com sucesso"}, 200


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
