from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from recommendations.controller import (
    get_random_recommendations,
    get_all_recommendations,
    delete_recommendation,
    clear_all_recommendations,
)

recommendations_bp = Blueprint("recommendations", __name__)
api = Namespace("recommendations", description="Operações relacionadas às recomendações de filmes")

# Modelo para o Swagger
recommendation_model = api.model(
    "Recommendation",
    {
        "tconst": fields.String(description="ID IMDB"),
        "title": fields.String(description="Título do filme"),
        "original_title": fields.String(description="Título original"),
        "year": fields.String(description="Ano de lançamento"),
        "director": fields.String(description="Diretor"),
        "genres": fields.String(description="Gêneros"),
        "imdb_rating": fields.String(description="Rating do IMDb"),
        "runtime": fields.String(description="Duração em minutos"),
        "position": fields.Integer(description="Posição na watchlist"),
        "url": fields.String(description="URL do IMDb"),
    },
)


@api.route("/random")
class RandomRecommendations(Resource):
    @api.doc("get_random_recommendations")
    @api.param("count", "Número de recomendações", type=int, default=6)
    @api.response(200, "Sucesso")
    def get(self):
        """Retorna recomendações aleatórias"""
        count = request.args.get("count", default=6, type=int)
        return get_random_recommendations(count)


@api.route("/all")
class AllRecommendations(Resource):
    @api.doc("get_all_recommendations")
    @api.param("page", "Número da página", type=int, default=1)
    @api.param("page_size", "Tamanho da página", type=int, default=10)
    @api.param("search_term", "Termo de busca", type=str)
    @api.response(200, "Sucesso")
    def get(self):
        """Retorna todas as recomendações com paginação"""
        page = request.args.get("page", default=1, type=int)
        page_size = request.args.get("page_size", default=10, type=int)
        search_term = request.args.get("search_term", default="", type=str)
        return get_all_recommendations(page, page_size, search_term)


@api.route("/<string:tconst>")
class RecommendationItem(Resource):
    @api.doc("delete_recommendation")
    @api.response(200, "Recomendação removida com sucesso")
    @api.response(404, "Recomendação não encontrada")
    def delete(self, tconst):
        """Remove uma recomendação"""
        return delete_recommendation(tconst)


@api.route("/clear")
class ClearRecommendations(Resource):
    @api.doc("clear_all_recommendations")
    @api.response(200, "Todas as recomendações foram removidas")
    def delete(self):
        """Remove todas as recomendações"""
        return clear_all_recommendations()


recommendations_bp.api = api

