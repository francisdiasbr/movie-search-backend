from flask import Blueprint
from flask_restx import Namespace, Resource, fields

from series.controller import (
    add_series,
    delete_series,
    edit_series,
    get_series,
    list_series,
)
from utils import json_body

series_bp = Blueprint("series", __name__)
api = Namespace("series", description="Séries de TV acompanhadas, com os dados do IMDb")

series_model = api.model(
    "Series",
    {
        "creators": fields.List(fields.String, description="Criadores"),
        "endYear": fields.Integer(description="Ano do fim, nulo se ainda no ar"),
        "episodes": fields.Integer(description="Total de episódios"),
        "genres": fields.List(fields.String, description="Gêneros"),
        "imdb_rating": fields.Float(description="Nota no IMDb"),
        "plot": fields.String(description="Sinopse"),
        "poster_url": fields.String(description="URL do pôster"),
        "primaryTitle": fields.String(description="Título"),
        "seasons": fields.Integer(description="Número de temporadas"),
        "startYear": fields.Integer(description="Ano de estreia"),
        "stars": fields.List(fields.String, description="Elenco principal"),
        "tconst": fields.String(description="ID IMDB"),
        "title_pt": fields.String(description="Título no Brasil, vazio quando é o original"),
        "watched": fields.Boolean(description="Já assistida"),
    },
)

series_edit_model = api.model(
    "SeriesEdit", {"watched": fields.Boolean(description="Já assistida")}
)

series_search_model = api.model(
    "SeriesSearch",
    {
        "filters": fields.Raw(description="Filtros para a busca"),
        "page": fields.Integer(description="Número da página", default=1),
        "page_size": fields.Integer(description="Tamanho da página", default=0),
        "search_term": fields.String(description="Termo de busca", default=""),
    },
)


@api.route("/search")
class SeriesSearch(Resource):
    @api.doc("search_series")
    @api.expect(series_search_model)
    @api.response(200, "Sucesso")
    def post(self):
        """Lista as séries, com busca por título"""
        body = json_body()
        return list_series(
            filters=body.get("filters", {}),
            page=body.get("page", 1),
            page_size=body.get("page_size", 0),
            search_term=body.get("search_term", ""),
        )


@api.route("/<string:tconst>")
class Series(Resource):
    @api.doc("get_series")
    @api.response(200, "Sucesso")
    @api.response(404, "Série não encontrada")
    def get(self, tconst):
        """Recupera uma série da lista"""
        return get_series(tconst)

    @api.doc("add_series")
    @api.response(201, "Série adicionada com sucesso")
    @api.response(400, "O título não é uma série")
    @api.response(404, "Título não encontrado no IMDb")
    @api.response(409, "Série já está na lista")
    @api.response(502, "IMDb não respondeu")
    def post(self, tconst):
        """Adiciona uma série pelo tconst do IMDb"""
        return add_series(tconst)

    @api.doc("update_series")
    @api.expect(series_edit_model)
    @api.response(200, "Série atualizada com sucesso")
    @api.response(404, "Série não encontrada")
    def put(self, tconst):
        """Atualiza uma série da lista"""
        return edit_series(tconst, json_body())

    @api.doc("delete_series")
    @api.response(200, "Série removida com sucesso")
    @api.response(404, "Série não encontrada")
    def delete(self, tconst):
        """Remove uma série da lista"""
        return delete_series(tconst)


series_bp.api = api
