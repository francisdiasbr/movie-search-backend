from flask import Blueprint
from flask_restx import Namespace, Resource, fields
from belas_artes.controller import get_recently_added

belas_artes_bp = Blueprint("belas_artes", __name__)
api = Namespace(
    "belas-artes", description="Catálogo do Belas Artes à la Carte com a nota do IMDb"
)

recent_movie_model = api.model(
    "BelasArtesMovie",
    {
        "id": fields.Integer(required=True, description="ID do título no Belas Artes"),
        "title": fields.String(required=True, description="Título em português"),
        "original_title": fields.String(required=True, description="Título original"),
        "year": fields.Integer(required=True, description="Ano de lançamento"),
        "director": fields.String(required=True, description="Direção"),
        "tconst": fields.String(
            description="IMDb ID (tconst), nulo quando o filme não foi encontrado",
            example="tt0086066",
        ),
        "imdb_rating": fields.Float(
            description="Nota no IMDb, nula quando não há", example=7.0
        ),
    },
)

recent_data_model = api.model(
    "BelasArtesRecentData",
    {"movies": fields.List(fields.Nested(recent_movie_model), required=True)},
)

recent_response_model = api.model(
    "BelasArtesRecentResponse",
    {"data": fields.Nested(recent_data_model, required=True)},
)


@api.route("/recent")
class RecentlyAdded(Resource):
    @api.doc("get_recently_added")
    @api.response(200, "Sucesso", recent_response_model)
    @api.response(404, "Seção não encontrada no catálogo")
    @api.response(502, "Belas Artes não respondeu")
    def get(self):
        """Filmes adicionados recentemente ao Belas Artes, com a nota do IMDb"""
        return get_recently_added()


belas_artes_bp.api = api
