from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from .controller import upload_image_to_s3, get_image_url, get_all_image_urls, delete_image_from_s3, update_image_subtitle

images_bp = Blueprint("images", __name__)
api = Namespace(
    "images",
    description="Operações relacionadas a imagens"
)

@api.route("/<string:tconst>")
class ImageOperations(Resource):
    @api.doc("upload_image")
    @api.response(200, "Upload realizado com sucesso")
    @api.response(400, "Arquivo não encontrado")
    @api.response(500, "Erro interno do servidor")
    def post(self, tconst):
        """Faz upload de uma imagem para o S3 associada a um filme específico"""
        if 'file' not in request.files:
            return {"status": 400, "message": "Arquivo não encontrado"}, 400
        
        file = request.files['file']
        BUCKET_NAME = 'themoviesearch'
        object_name = f"{tconst}/{file.filename}"
        return upload_image_to_s3(file, BUCKET_NAME, object_name)

    @api.doc("get_all_image_urls")
    @api.response(200, "URLs geradas com sucesso")
    @api.response(404, "Imagens não encontradas")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst):
        """Gera todas as URLs públicas diretas para imagens associadas a um tconst"""
        BUCKET_NAME = 'themoviesearch'
        return get_all_image_urls(BUCKET_NAME, tconst)

@api.route("/<string:tconst>/<string:filename>")
class ImageDetailOperations(Resource):
    @api.doc("get_public_image_url")
    @api.response(200, "URL gerada com sucesso")
    @api.response(404, "Imagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst, filename):
        """Gera uma URL pública direta para acessar a imagem no S3"""
        BUCKET_NAME = 'themoviesearch'
        return get_image_url(BUCKET_NAME, tconst, filename)

    @api.doc("delete_image")
    @api.response(200, "Imagem deletada com sucesso")
    @api.response(404, "Imagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def delete(self, tconst, filename):
        """Deleta uma imagem específica de um bucket S3"""
        BUCKET_NAME = 'themoviesearch'
        return delete_image_from_s3(BUCKET_NAME, tconst, filename)

    @api.doc("update_image_subtitle")
    @api.response(200, "Legenda atualizada com sucesso")
    @api.response(500, "Erro interno do servidor")
    def put(self, tconst, filename):
        """Atualiza a legenda de uma imagem específica"""
        data = request.get_json()
        subtitle = data.get('subtitle', '')
        BUCKET_NAME = 'themoviesearch'
        return update_image_subtitle(BUCKET_NAME, tconst, filename, subtitle)

images_bp.api = api
