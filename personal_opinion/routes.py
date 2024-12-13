from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields
from .controller import insert_personal_opinion, get_personal_opinions, delete_personal_opinion, get_all_personal_opinions, search_personal_opinions

personal_opinion_bp = Blueprint("personal_opinion", __name__)
api = Namespace(
    "personal-opinion",
    description="Operações relacionadas a opiniões pessoais"
)

# Modelos para o Swagger
opinion_model = api.model(
    "PersonalOpinion",
    {
        "opinion": fields.String(description="Opinião pessoal", required=True),
        "rate": fields.String(description="Avaliação", required=True)
    }
)

search_model = api.model(
    "SearchPersonalOpinion",
    {
        "filters": fields.Raw(description="Filtros de pesquisa"),
        "page": fields.Integer(description="Número da página", default=1),
        "page_size": fields.Integer(description="Tamanho da página", default=10)
    }
)

@api.route("/")
class AllPersonalOpinions(Resource):
    @api.doc("get_all_personal_opinions")
    @api.response(200, "Sucesso")
    @api.response(500, "Erro interno do servidor")
    def get(self):
        """Recupera todas as opiniões pessoais"""
        return get_all_personal_opinions()

    @api.doc("search_personal_opinions")
    @api.expect(search_model)
    @api.response(200, "Sucesso")
    @api.response(400, "Dados de entrada inválidos")
    @api.response(500, "Erro interno do servidor")
    def post(self):
        """Pesquisa opiniões pessoais com base em filtros e paginação"""
        data = request.get_json()
        if not isinstance(data, dict):
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
        
        filters = data.get("filters", {})
        page = data.get("page", 1)
        page_size = data.get("page_size", 10)
        
        return search_personal_opinions(filters, page, page_size)

@api.route("/<string:tconst>")
class PersonalOpinion(Resource):
    @api.doc("get_personal_opinions")
    @api.response(200, "Sucesso")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst):
        """Recupera todas as opiniões pessoais para um filme específico"""
        return get_personal_opinions(tconst)

    @api.doc("insert_personal_opinion")
    @api.expect(opinion_model)
    @api.response(201, "Opinião inserida com sucesso")
    @api.response(400, "Dados de entrada inválidos")
    @api.response(500, "Erro interno do servidor")
    def post(self, tconst):
        """Insere uma nova opinião pessoal para um filme específico"""
        data = request.get_json()
        if not data or "opinion" not in data or "rate" not in data:
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
        return insert_personal_opinion(tconst, data["opinion"], data["rate"])

@api.route("/<string:tconst>/<string:opinion_id>")
class PersonalOpinionDelete(Resource):
    @api.doc("delete_personal_opinion")
    @api.response(200, "Opinião deletada com sucesso")
    @api.response(404, "Opinião não encontrada")
    @api.response(500, "Erro interno do servidor")
    def delete(self, tconst, opinion_id):
        """Deleta uma opinião pessoal específica"""
        return delete_personal_opinion(tconst, opinion_id)

personal_opinion_bp.api = api
