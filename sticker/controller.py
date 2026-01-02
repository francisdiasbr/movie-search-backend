import os
from typing import Optional
import config
import boto3
from botocore.exceptions import ClientError
import time
import base64
import hashlib




def save_sticker_image_to_s3(image_data: bytes, tconst: str) -> str:
    """Salva a imagem do sticker no S3 e retorna o nome do arquivo"""
    try:
        from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name="us-east-2",
        )
        
        BUCKET_NAME = "themoviesearch"
        STICKERS_PREFIX = "stickers"
        
        # Gerar nome único baseado no tconst e timestamp
        timestamp = str(int(time.time()))
        filename = f"{tconst}_{timestamp}.png"
        s3_key = f"{STICKERS_PREFIX}/{tconst}/{filename}"
        
        # Upload da imagem para o S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=image_data,
            ContentType="image/png"
        )
        
        return filename
    except Exception as e:
        return None


def get_sticker_image_from_s3(filename: str, tconst: str) -> tuple:
    """Busca uma imagem de sticker salva no S3"""
    try:
        from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name="us-east-2",
        )
        
        BUCKET_NAME = "themoviesearch"
        STICKERS_PREFIX = "stickers"
        s3_key = f"{STICKERS_PREFIX}/{tconst}/{filename}"
        
        # Buscar a imagem do S3
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        image_data = response["Body"].read()
        
        return image_data, "image/png"
    except Exception as e:
        return None, None


def get_movie_image(tconst: str, sequential_id: int = None):
    """Busca uma imagem específica de um filme no S3 por ID sequencial ou a primeira se sequential_id não for fornecido"""
    try:
        from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, get_mongo_collection
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name="us-east-2",
        )
        
        BUCKET_NAME = "themoviesearch"
        MAIN_PREFIX = "main-images"
        collection = get_mongo_collection("main-images")
        
        # Se sequential_id foi fornecido, buscar imagem específica
        if sequential_id is not None:
            # Buscar metadados da imagem no MongoDB
            image_doc = collection.find_one({
                "tconst": tconst,
                "sequential_id": int(sequential_id)
            })
            
            if not image_doc:
                return None, None
            
            filename = image_doc["filename"]
            object_name = f"{MAIN_PREFIX}/{tconst}/{filename}"
            
            try:
                image_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_name)
                image_bytes = image_response["Body"].read()
                
                # Determinar o tipo MIME baseado na extensão
                file_extension = filename.lower()
                if file_extension.endswith(".png"):
                    mime_type = "image/png"
                elif file_extension.endswith((".jpg", ".jpeg")):
                    mime_type = "image/jpeg"
                else:
                    mime_type = "image/jpeg"  # fallback
                
                return image_bytes, mime_type
            except Exception:
                return None, None
        
        # Se sequential_id não foi fornecido, buscar a primeira imagem (ID sequencial 1)
        image_doc = collection.find_one({
            "tconst": tconst,
            "sequential_id": 1
        })
        
        if not image_doc:
            return None, None
        
        filename = image_doc["filename"]
        object_name = f"{MAIN_PREFIX}/{tconst}/{filename}"
        
        try:
            image_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_name)
            image_bytes = image_response["Body"].read()
            
            # Determinar o tipo MIME baseado na extensão
            file_extension = filename.lower()
            if file_extension.endswith(".png"):
                mime_type = "image/png"
            elif file_extension.endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            else:
                mime_type = "image/jpeg"  # fallback
            
            return image_bytes, mime_type
        except Exception:
            return None, None
        
    except Exception as e:
        return None, None


def list_movie_images(tconst: str):
    """Lista todas as imagens disponíveis de um filme no S3 com ID sequencial"""
    try:
        from config import get_mongo_collection
        
        collection = get_mongo_collection("main-images")
        
        # Buscar todas as imagens do tconst no MongoDB, ordenadas por ID sequencial
        images_metadata = collection.find(
            {"tconst": tconst}
        ).sort("sequential_id", 1)
        
        image_list = []
        for image_doc in images_metadata:
            filename = image_doc["filename"]
            sequential_id = image_doc["sequential_id"]
            subtitle_en = image_doc.get("subtitle_en", "")
            subtitle_pt = image_doc.get("subtitle_pt", "")
            created_at = image_doc.get("created_at", "")
            
            image_list.append({
                "filename": filename,
                "sequential_id": sequential_id,
                "subtitle_en": subtitle_en,
                "subtitle_pt": subtitle_pt,
                "created_at": created_at.isoformat() if created_at else ""
            })
        
        return image_list
        
    except Exception as e:
        return []


def list_all_stickers(tconst: str):
    """Lista todos os stickers disponíveis de um filme no S3"""
    try:
        from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name="us-east-2",
        )
        
        BUCKET_NAME = "themoviesearch"
        STICKERS_PREFIX = "stickers"
        
        # Listar todos os objetos do tconst no S3
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME, 
            Prefix=f"{STICKERS_PREFIX}/{tconst}/"
        )
        
        stickers = []
        objects = response.get("Contents", [])
        
        # Ordenar por data de modificação (mais recente primeiro)
        objects.sort(key=lambda x: x["LastModified"], reverse=True)
        
        for obj in objects:
            filename = obj["Key"].split("/")[-1]
            last_modified = obj["LastModified"]
            size = obj["Size"]
            
            stickers.append({
                "filename": filename,
                "last_modified": last_modified.isoformat(),
                "size": size,
                "url": f"https://themoviesearch.s3.us-east-2.amazonaws.com/stickers/{tconst}/{filename}"
            })
        
        return stickers
        
    except Exception as e:
        return []


def generate_sticker_text(
    image_bytes: Optional[bytes] = None,
    image_mime_type: Optional[str] = None,
    image_url: Optional[str] = None,
    tconst: Optional[str] = None,
    sequential_id: Optional[int] = None,
):
    try:
        # Lazy import to avoid import cost if unused
        from google import genai
        from google.genai.types import Content, Part
        import requests

        api_key = os.getenv("GEMINI_API_KEY") 
        client = genai.Client(api_key=api_key)

        # Prompt fixo para criação de sticker
        text_prompt = "Crie um sticker do rosto do personagem principal. desconsidere todo o resto. coloque uma borda branca grossa no contorno do rosto do personagem principal. Desconsidere o fundo, deixe o fundo branco, e deixe somente o rosto do personagem principal e a borda branca. Se houver mais de um personagem, faça no máximo 3 stickers, um  para cada personagem."

        image_part = None
        
        # Se tconst foi fornecido, buscar imagem do filme (específica ou primeira)
        if tconst and isinstance(tconst, str):
            movie_image_bytes, movie_mime_type = get_movie_image(tconst, sequential_id)
            if movie_image_bytes:
                image_bytes = movie_image_bytes
                image_mime_type = movie_mime_type
        
        # If URL provided, fetch into bytes (só se não tiver imagem do filme)
        elif image_url and isinstance(image_url, str):
            try:
                resp = requests.get(image_url, timeout=10)
                resp.raise_for_status()
                image_bytes = resp.content
                if not image_mime_type:
                    image_mime_type = resp.headers.get("Content-Type", None)
            except Exception:
                # Ignore image on fetch failure; will fallback to text-only
                image_bytes = None

        if image_bytes and isinstance(image_bytes, (bytes, bytearray)):
            if not image_mime_type:
                # Reasonable default; client should pass explicit type when possible
                image_mime_type = "image/png"
            image_part = Part.from_bytes(
                data=bytes(image_bytes), mime_type=image_mime_type
            )

        # Decide contents based on available inputs
        if image_part is not None or text_prompt is not None:
            parts = []
            if image_part is not None:
                parts.append(image_part)
            if text_prompt is not None:
                parts.append(Part.from_text(text_prompt))
            contents = [Content(role="user", parts=parts)]
        else:
            # Fallback default when nothing provided
            contents = "Explain how AI works in a few words"

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image-preview",
                contents=contents
            )
            
        except Exception as gemini_error:
            return (
                {
                    "status": 500,
                    "message": "Erro na requisição para o Gemini",
                    "error": str(gemini_error),
                    "error_type": type(gemini_error).__name__,
                },
                500,
            )

        # Verificar se a resposta contém uma imagem ou texto
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            
            if hasattr(candidate, 'content') and candidate.content:
                text_result = None
                image_data = None
                image_mime_type = None
                
                # Verificar todas as partes da resposta
                if hasattr(candidate.content, 'parts'):
                    for i, part in enumerate(candidate.content.parts):
                        if hasattr(part, 'inline_data') and part.inline_data:
                            # Encontrou uma imagem
                            image_data = part.inline_data.data
                            image_mime_type = part.inline_data.mime_type or "image/png"
                        elif hasattr(part, 'text') and part.text:
                            # Encontrou texto
                            text_result = part.text
                
                # Se há imagem, salvar no S3 e retornar a imagem diretamente
                if image_data:
                    filename = save_sticker_image_to_s3(image_data, tconst)
                    if filename:
                        # Retornar a imagem diretamente com headers apropriados
                        return image_data, 200, {"Content-Type": "image/png"}
                
                # Se há texto, retornar erro (não deve acontecer)
                if text_result:
                    return {
                        "status": 500,
                        "message": "Gemini retornou texto em vez de imagem",
                        "tconst": tconst
                    }, 500
        
        # Fallback: se não conseguiu processar a resposta
        return (
            {
                "status": 500,
                "message": "Resposta do Gemini não pôde ser processada",
                "prompt": text_prompt,
                "has_image": image_part is not None,
                "tconst": tconst,
            },
            500,
        )
    except Exception as error:
        return (
            {
                "status": 500,
                "message": "Erro ao gerar conteúdo com Gemini",
                "error": str(error),
            },
            500,
        )


