from flask import Blueprint
from flask_restx import Namespace, Resource, fields

from favorites.controller import (
    delete_favorited_movie,
    edit_favorited_movie,
    favorite_movie,
    get_favorited_movie,
    get_favorited_movies,
)
from utils import json_body

favorites_bp = Blueprint("favorites", __name__)
api = Namespace("favorites", description="Operações relacionadas aos filmes favoritos")

# Modelos para o Swagger
favorite_movie_model = api.model(
    "FavoriteMovie",
    {
        "country": fields.String(description="País"),
        "created_at": fields.String(description="Data de criação"),
        "director": fields.String(description="Diretor"),
        "genres": fields.List(fields.String, description="Gêneros"),
        "magnet_link": fields.String(description="Magnet link"),
        "plot": fields.String(description="Sinopse"),
        "plot_keywords": fields.List(fields.String, description="Palavras-chave"),
        "primaryTitle": fields.String(description="Título do filme"),
        "quote": fields.String(description="Citação"),
        "references": fields.List(fields.String, description="Referências"),
        "soundtrack": fields.String(description="Link da trilha sonora"),
        "startYear": fields.Integer(description="Ano de lançamento"),
        "stars": fields.List(fields.String, description="Atores principais"),
        "subtitle_url": fields.String(description="URL da legenda"),
        "tconst": fields.String(description="ID IMDB"),
        "trivia": fields.String(description="Curiosidades"),
        "watched": fields.Boolean(description="Já assistido"),
        "wiki": fields.String(description="Link da Wikipedia"),
        "writers": fields.List(fields.String, description="Roteiristas"),
    },
)

favorite_search_model = api.model(
    "FavoriteSearch",
    {
        "filters": fields.Raw(description="Filtros para a busca"),
        "page": fields.Integer(description="Número da página", default=1),
        "page_size": fields.Integer(description="Tamanho da página", default=10),
        "search_term": fields.String(description="Termo de busca", default=""),
    },
)


# Define the search route first
@api.route("/search")
class FavoriteMovieSearch(Resource):
    @api.doc("search_favorite_movies")
    @api.expect(favorite_search_model)
    @api.response(200, "Sucesso")
    def post(self):
        """Pesquisa filmes favoritados"""
        request_data = json_body()
        return get_favorited_movies(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 0),
            search_term=request_data.get("search_term", ""),
        )


# Define other routes after the search route
@api.route("/<string:tconst>")
class FavoriteMovie(Resource):
    @api.doc("get_favorite_movie")
    @api.response(200, "Sucesso")
    @api.response(404, "Filme não encontrado")
    def get(self, tconst):
        """Recupera um filme favoritado"""
        return get_favorited_movie(tconst)

    @api.doc("add_favorite_movie")
    @api.response(201, "Filme adicionado com sucesso")
    @api.response(409, "Filme já está na lista")
    def post(self, tconst):
        """Adiciona um filme aos favoritos"""
        return favorite_movie(tconst)

    @api.doc("update_favorite_movie")
    @api.expect(favorite_movie_model)
    @api.response(200, "Filme atualizado com sucesso")
    @api.response(404, "Filme não encontrado")
    def put(self, tconst):
        """Atualiza um filme favoritado"""
        return edit_favorited_movie(tconst, json_body())

    @api.doc("delete_favorite_movie")
    @api.response(200, "Filme removido com sucesso")
    @api.response(404, "Filme não encontrado")
    def delete(self, tconst):
        """Remove um filme dos favoritos"""
        return delete_favorited_movie(tconst)


favorites_bp.api = api
