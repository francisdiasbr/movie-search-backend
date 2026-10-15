from flask import Blueprint, request
from flask_restx import Namespace, Resource

from .controller import (
    upload_image_to_s3,
    get_all_image_urls,
    delete_image_from_s3,
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
            return {"message": "Arquivo não encontrado"}, 400

        return upload_image_to_s3(
            request.files["file"],
            tconst,
            request.form.get("subtitle_en", ""),
            request.form.get("subtitle_pt", ""),
        )

    @api.doc("get_all_image_urls")
    @api.response(200, "URLs geradas com sucesso")
    @api.response(404, "Imagens não encontradas")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst):
        """Gera todas as URLs públicas diretas para imagens associadas a um tconst"""
        return get_all_image_urls(tconst)


@api.route("/<string:tconst>/<string:filename>")
class ImageDetailOperations(Resource):
    @api.doc("delete_image")
    @api.response(200, "Imagem deletada com sucesso")
    @api.response(404, "Imagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def delete(self, tconst, filename):
        """Deleta uma imagem específica do bucket S3"""
        return delete_image_from_s3(tconst, filename)


main_images_bp.api = api


