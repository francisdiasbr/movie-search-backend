from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields
from keywords.controller import (
    add_keyword,
    get_favorited_keywords,
    delete_favorited_keyword,
    suggest_movies_by_keywords,
)

keywords_bp = Blueprint("keywords", __name__)
api = Namespace(
    "keywords", description="Operações relacionadas às palavras-chave favoritas"
)

keyword_model = api.model(
    "KeywordInput",
    {"keyword": fields.String(required=True, description="Palavra-chave do filme")},
)

movie_suggestion_model = api.model(
    "MovieSuggestion",
    {
        "title": fields.String(required=True, description="Título do filme"),
        "year": fields.Integer(required=True, description="Ano de lançamento"),
        "tconst": fields.String(
            required=True,
            description="IMDb ID (tconst) do filme",
            example="tt0068646",
        ),
        "description": fields.String(
            required=True, description="Breve descrição (2-3 linhas)"
        ),
        "relevance": fields.String(
            required=True,
            description=
                "Explicação objetiva de como as palavras-chave aparecem no filme",
        ),
    },
)

movie_suggestions_data_model = api.model(
    "MovieSuggestionsData",
    {"movies": fields.List(fields.Nested(movie_suggestion_model), required=True)},
)

movie_suggestions_response_model = api.model(
    "MovieSuggestionsResponse",
    {"data": fields.Nested(movie_suggestions_data_model, required=True)},
)

keywords_model = api.model(
    "KeywordsInput",
    {
        "keywords": fields.List(
            fields.String, required=True, description="Lista de palavras-chave"
        )
    },
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


@api.route("/suggest-movies")
class MovieSuggestions(Resource):
    @api.doc("suggest_movies")
    @api.expect(keywords_model)
    @api.marshal_with(movie_suggestions_response_model, code=200, description="Sugestões geradas com sucesso")
    @api.response(400, "Lista de keywords inválida")
    @api.response(500, "Erro ao gerar sugestões")
    def post(self):
        """Sugere filmes baseado em uma lista de palavras-chave"""
        try:
            request_data = request.get_json() or {}

            if not isinstance(request_data, dict) or "keywords" not in request_data:
                return {"data": "Lista de keywords é obrigatória"}, 400

            keywords = request_data["keywords"]
            if not isinstance(keywords, list) or not keywords:
                return {"data": "Lista de keywords inválida"}, 400

            return suggest_movies_by_keywords(keywords)

        except Exception as e:
            print(f"Error processing request: {e}")
            return {"data": "Formato de requisição inválido"}, 400


keywords_bp.api = api
