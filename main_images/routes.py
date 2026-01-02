from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from .controller import (
    upload_image_to_s3,
    get_image_url,
    get_all_image_urls,
    get_image_by_sequential_id,
    delete_image_from_s3,
    update_image_subtitle,
)

main_images_bp = Blueprint("main-images", __name__)
api = Namespace("main-images", description="Operações relacionadas a main-images")


@api.route("/<string:tconst>")
class ImageOperations(Resource):
    @api.doc("upload_image")
    @api.response(200, "Upload realizado com sucesso")
    @api.response(400, "Arquivo não encontrado")
    @api.response(500, "Erro interno do servidor")
    def post(self, tconst):
        """Faz upload de uma imagem para o S3 associada a um filme específico com ID sequencial"""
        if "file" not in request.files:
            return {"status": 400, "message": "Arquivo não encontrado"}, 400

        file = request.files["file"]
        data = request.form
        subtitle_en = data.get("subtitle_en", "")
        subtitle_pt = data.get("subtitle_pt", "")
        
        BUCKET_NAME = "themoviesearch"
        return upload_image_to_s3(file, BUCKET_NAME, tconst, subtitle_en, subtitle_pt)

    @api.doc("get_all_image_urls")
    @api.response(200, "URLs geradas com sucesso")
    @api.response(404, "Imagens não encontradas")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst):
        """Gera todas as URLs públicas diretas para imagens associadas a um tconst"""
        BUCKET_NAME = "themoviesearch"
        return get_all_image_urls(BUCKET_NAME, tconst)


@api.route("/<string:tconst>/id/<int:sequential_id>")
class ImageByIdOperations(Resource):
    @api.doc("get_image_by_sequential_id")
    @api.response(200, "Imagem encontrada com sucesso")
    @api.response(404, "Imagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst, sequential_id):
        """Busca uma imagem específica pelo ID sequencial"""
        BUCKET_NAME = "themoviesearch"
        return get_image_by_sequential_id(BUCKET_NAME, tconst, sequential_id)


@api.route("/<string:tconst>/<string:filename>")
class ImageDetailOperations(Resource):
    @api.doc("get_public_image_url")
    @api.response(200, "URL gerada com sucesso")
    @api.response(404, "Imagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst, filename):
        """Gera uma URL pública direta para acessar a imagem no S3"""
        BUCKET_NAME = "themoviesearch"
        return get_image_url(BUCKET_NAME, tconst, filename)

    @api.doc("delete_image")
    @api.response(200, "Imagem deletada com sucesso")
    @api.response(404, "Imagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def delete(self, tconst, filename):
        """Deleta uma imagem específica de um bucket S3"""
        BUCKET_NAME = "themoviesearch"
        return delete_image_from_s3(BUCKET_NAME, tconst, filename)

    @api.doc("update_image_subtitle")
    @api.response(200, "Legendas atualizadas com sucesso")
    @api.response(500, "Erro interno do servidor")
    def put(self, tconst, filename):
        """Atualiza as legendas de uma imagem específica"""
        data = request.get_json()
        subtitle_en = data.get("subtitle_en", "")
        subtitle_pt = data.get("subtitle_pt", "")
        BUCKET_NAME = "themoviesearch"
        return update_image_subtitle(BUCKET_NAME, tconst, filename, subtitle_en, subtitle_pt)


main_images_bp.api = api


