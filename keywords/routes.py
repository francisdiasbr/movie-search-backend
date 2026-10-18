from flask import Blueprint
from flask_restx import Namespace, Resource, fields
from keywords.controller import (
    add_keyword,
    get_favorited_keywords,
    delete_favorited_keyword,
    suggest_movies_by_keywords,
)
from utils import json_body

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
        "original_title": fields.String(
            required=True, description="Título original, como no IMDb"
        ),
        "year": fields.Integer(required=True, description="Ano de lançamento"),
        "tconst": fields.String(
            required=True,
            description="IMDb ID (tconst) do filme",
            example="tt0068646",
        ),
        "description": fields.String(
            required=True, description="Sinopse do IMDb (vazia quando não há)"
        ),
        "relevance": fields.String(
            required=True,
            description="Quais das palavras-chave o IMDb associa ao filme",
        ),
        "genres": fields.List(
            fields.String,
            required=True,
            description="Gêneros do filme, como listados no IMDb",
            example=["Drama", "Romance"],
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
        return add_keyword(json_body().get("keyword"))


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
    @api.marshal_with(
        movie_suggestions_response_model,
        code=200,
        description="Sugestões geradas com sucesso",
    )
    @api.response(400, "Lista de keywords inválida")
    @api.response(502, "IMDb não respondeu à busca")
    def post(self):
        """Sugere filmes baseado em uma lista de palavras-chave"""
        keywords = json_body().get("keywords")
        if not isinstance(keywords, list) or not keywords:
            return {"message": "Lista de keywords inválida"}, 400
        return suggest_movies_by_keywords(keywords)


keywords_bp.api = api
