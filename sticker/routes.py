from flask import Blueprint, request, Response
from flask_restx import Namespace, Resource, fields
from botocore.exceptions import ClientError

from sticker.controller import generate_sticker_text, get_sticker_image_from_s3, list_movie_images, list_all_stickers


sticker_bp = Blueprint("sticker", __name__)
api = Namespace("sticker", description="Operações do Gemini para sticker")

@api.route("/generate/<string:tconst>")
class StickerGenerate(Resource):
    @api.doc("generate_sticker_text")
    @api.response(200, "Sucesso")
    @api.response(500, "Falha ao gerar")
    def post(self, tconst):
        # Gerar sticker da primeira imagem (ID sequencial 1)
        result = generate_sticker_text(tconst=tconst, sequential_id=1)
        
        # Se o resultado é uma imagem (tupla com 3 elementos), retornar como Response
        if isinstance(result, tuple) and len(result) == 3:
            image_data, status_code, headers = result
            return Response(
                response=image_data,
                status=status_code,
                headers=headers
            )
        
        # Caso contrário, retornar JSON normal (erro)
        return result


@api.route("/generate/<string:tconst>/<int:sequential_id>")
class StickerGenerateWithId(Resource):
    @api.doc("generate_sticker_text_with_id")
    @api.response(200, "Sucesso")
    @api.response(500, "Falha ao gerar")
    def post(self, tconst, sequential_id):
        # Gerar sticker da imagem específica pelo ID sequencial
        result = generate_sticker_text(tconst=tconst, sequential_id=sequential_id)
        
        # Se o resultado é uma imagem (tupla com 3 elementos), retornar como Response
        if isinstance(result, tuple) and len(result) == 3:
            image_data, status_code, headers = result
            return Response(
                response=image_data,
                status=status_code,
                headers=headers
            )
        
        # Caso contrário, retornar JSON normal (erro)
        return result


@api.route("/images/<string:tconst>")
class StickerImages(Resource):
    @api.doc("list_movie_images")
    @api.response(200, "Lista de imagens disponíveis")
    @api.response(500, "Erro ao listar imagens")
    def get(self, tconst):
        # Listar todas as imagens disponíveis para o filme
        images = list_movie_images(tconst)
        
        if images is None:
            return {"status": 500, "message": "Erro ao listar imagens"}, 500
        
        return {"images": images}, 200


@api.route("/all/<string:tconst>")
class StickerAll(Resource):
    @api.doc("list_all_stickers")
    @api.response(200, "Lista de todos os stickers do filme")
    @api.response(404, "Nenhum sticker encontrado")
    def get(self, tconst):
        # Listar todos os stickers disponíveis para o filme
        stickers = list_all_stickers(tconst)
        
        if not stickers:
            return {"status": 404, "message": "Nenhum sticker encontrado para este filme"}, 404
        
        return {"stickers": stickers, "count": len(stickers)}, 200


@api.route("/<string:tconst>/<string:filename>")
class StickerSpecific(Resource):
    @api.doc("get_specific_sticker")
    @api.response(200, "Imagem do sticker específico")
    @api.response(404, "Sticker não encontrado")
    def get(self, tconst, filename):
        # Buscar sticker específico no S3
        image_data, mime_type = get_sticker_image_from_s3(filename, tconst)
        
        if image_data:
            return Response(
                response=image_data,
                status=200,
                headers={"Content-Type": mime_type}
            )
        else:
            return {"status": 404, "message": "Sticker não encontrado"}, 404
    
    @api.doc("delete_specific_sticker")
    @api.response(200, "Sticker removido com sucesso")
    @api.response(404, "Sticker não encontrado")
    def delete(self, tconst, filename):
        # Remover sticker específico do S3
        try:
            import boto3
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
            
            # Verificar se o objeto existe
            try:
                s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return {"status": 404, "message": "Sticker não encontrado"}, 404
                raise
            
            # Deletar o objeto
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
            
            return {"status": 200, "message": "Sticker removido com sucesso"}, 200
            
        except Exception as e:
            return {"status": 500, "message": f"Erro ao remover sticker: {str(e)}"}, 500


@api.route("/<string:tconst>")
class StickerImage(Resource):
    @api.doc("get_sticker_image")
    @api.response(200, "Imagem do sticker")
    @api.response(404, "Sticker não encontrado")
    def get(self, tconst):
        # Buscar o sticker mais recente para o tconst no S3
        import boto3
        from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        
        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name="us-east-2",
            )
            
            BUCKET_NAME = "themoviesearch"
            STICKERS_PREFIX = "stickers"
            
            # Listar objetos do tconst no S3
            response = s3_client.list_objects_v2(
                Bucket=BUCKET_NAME, 
                Prefix=f"{STICKERS_PREFIX}/{tconst}/"
            )
            
            # Pegar a primeira imagem (ordenada por data de modificação)
            images = response.get("Contents", [])
            if not images:
                return {"status": 404, "message": "Sticker não encontrado para este filme"}, 404
            
            # Ordenar por data de modificação e pegar a mais recente
            images.sort(key=lambda x: x["LastModified"], reverse=True)
            latest_image = images[0]
            filename = latest_image["Key"].split("/")[-1]
            
            # Buscar e retornar a imagem do sticker
            image_data, mime_type = get_sticker_image_from_s3(filename, tconst)
            
            if image_data:
                return Response(
                    response=image_data,
                    status=200,
                    headers={"Content-Type": mime_type}
                )
            else:
                return {"status": 404, "message": "Erro ao carregar sticker"}, 404
                
        except Exception as e:
            return {"status": 500, "message": f"Erro ao buscar sticker: {str(e)}"}, 500


sticker_bp.api = api


