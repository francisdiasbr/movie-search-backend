from flask import request, jsonify
from datetime import datetime
from bson import ObjectId
import boto3
import re
from botocore.exceptions import ClientError
from urllib.parse import quote_plus, quote

from config import get_mongo_collection, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


COLLECTION_NAME = "images"



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


# def get_image_url(bucket_name, tconst, filename, expiration=3600):
#     """Gera uma URL pré-assinada para acessar um arquivo no S3"""
#     s3_client = boto3.client(
#         's3',
#         aws_access_key_id=AWS_ACCESS_KEY_ID,
#         aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#         region_name='us-east-2'
#     )
    
#     object_name = f"{tconst}/{quote(filename)}"
    
#     try:
#         response = s3_client.generate_presigned_url('get_object',
#                                                     Params={'Bucket': bucket_name, 'Key': object_name},
#                                                     ExpiresIn=expiration)
#     except ClientError as e:
#         print(f"Erro ao gerar URL pré-assinada: {e}")
#         return {"status": 500, "message": "Erro ao gerar URL pré-assinada"}, 500

#     return {"url": response}, 200


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


