from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields
from keywords.controller import (
    add_keyword,
    get_favorited_keywords,
    delete_favorited_keyword,
)

keywords_bp = Blueprint("keywords", __name__)
api = Namespace(
    "keywords", description="Operações relacionadas às palavras-chave favoritas"
)

keyword_model = api.model(
    "KeywordInput",
    {"keyword": fields.String(required=True, description="Palavra-chave do filme")},
)


@api.route("/")
class KeywordList(Resource):
    @api.doc("get_favorited_keywords")
    @api.response(200, "Sucesso")
    def get(self):
        """Recupera todas as palavras-chave favoritas"""
        return get_favorited_keywords()

    @api.doc("add_keyword")
    @api.expect(keyword_model)
    @api.response(201, "Palavra-chave adicionada com sucesso")
    @api.response(409, "Palavra-chave já está na lista")
    @api.response(400, "Palavra-chave é obrigatória")
    def post(self):
        """Adiciona uma palavra-chave aos favoritos"""
        try:
            request_data = request.get_json() or {}

            if not isinstance(request_data, dict) or "keyword" not in request_data:
                return {"data": "Keyword is required in request body"}, 400

            keyword = str(request_data["keyword"]).strip()
            if not keyword:
                return {"data": "Keyword cannot be empty"}, 400

            return add_keyword(keyword)

        except Exception as e:
            print(f"Error processing request: {e}")
            return {"data": "Invalid request format"}, 400


@api.route("/<string:keyword>")
class Keyword(Resource):
    @api.doc("delete_favorite_keyword")
    @api.response(200, "Palavra-chave removida com sucesso")
    @api.response(404, "Palavra-chave não encontrada")
    def delete(self, keyword):
        """Remove uma palavra-chave dos favoritos"""
        return delete_favorited_keyword(keyword)


keywords_bp.api = api
