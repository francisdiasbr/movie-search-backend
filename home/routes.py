from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from home.controller import get_blogpost_cards

home_bp = Blueprint("home", __name__)
api = Namespace(
    "home",
    description="Endpoints específicos para a página Home",
)

# Modelos para o Swagger
blog_search_model = api.model(
    "BlogSearch",
    {
        "filters": fields.Raw(description="Filtros para a busca"),
        "page": fields.Integer(description="Número da página", default=1),
        "page_size": fields.Integer(description="Tamanho da página", default=10),
    },
)


@api.route("/cards")
class HomeCards(Resource):
    @api.doc("get_home_cards")
    @api.expect(blog_search_model)
    @api.response(200, "Sucesso")
    @api.response(400, "Dados de entrada inválidos")
    def post(self):
        """Retorna apenas dados otimizados para cards na Home (tconst, primaryTitle, created_at, imageUrl)"""
        request_data = request.get_json()
        
        if not isinstance(request_data, dict):
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400

        return get_blogpost_cards(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 10),
        )


home_bp.api = api
