import logging
import mimetypes
import re
from datetime import datetime
from pathlib import PurePosixPath

import boto3
from botocore.exceptions import ClientError

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    MAIN_IMAGES_COLLECTION,
    S3_BUCKET,
    DatabaseUnavailable,
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

    # Images are stored as <sequential_id>.<ext> under the movie's prefix.
    sequential_id = get_next_sequential_id(tconst)
    extension = PurePosixPath(file.filename or "").suffix.lower()
    new_filename = f"{sequential_id}{extension}"
    object_name = f"{MAIN_PREFIX}/{tconst}/{new_filename}"
    content_type = mimetypes.types_map.get(extension, "application/octet-stream")

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
    except DatabaseUnavailable:
        # The metadata insert lost Mongo: app.py answers 503, not a S3 error.
        raise
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
