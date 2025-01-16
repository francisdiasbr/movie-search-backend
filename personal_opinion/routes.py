from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields
from .controller import insert_personal_opinion, get_personal_opinion, delete_personal_opinion, get_all_personal_opinions, search_personal_opinions, update_personal_opinion

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
        "enjoying_1": fields.String(description="Enjoying 1", required=True),
        "enjoying_2": fields.String(description="Enjoying 2", required=True)
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

update_opinion_model = api.model(
    "UpdatePersonalOpinion",
    {
        "opinion": fields.String(description="Opinião pessoal", required=False),
        "enjoying_1": fields.String(description="Enjoying 1", required=False),
        "enjoying_2": fields.String(description="Enjoying 2", required=False)
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
    @api.doc("get_personal_opinion")
    @api.response(200, "Sucesso")
    @api.response(404, "Opinião não encontrada")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst):
        """Recupera a opinião pessoal para um filme específico"""
        return get_personal_opinion(tconst)

    @api.doc("insert_personal_opinion")
    @api.expect(opinion_model)
    @api.response(201, "Opinião inserida com sucesso")
    @api.response(400, "Dados de entrada inválidos")
    @api.response(500, "Erro interno do servidor")
    def post(self, tconst):
        """Insere uma nova opinião pessoal para um filme específico"""
        data = request.get_json()
        if not data or "opinion" not in data or "enjoying_1" not in data or "enjoying_2" not in data:
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
        return insert_personal_opinion(tconst, data["opinion"], data["enjoying_1"], data["enjoying_2"])

    @api.doc("update_personal_opinion")
    @api.expect(update_opinion_model)
    @api.response(200, "Opinião atualizada com sucesso")
    @api.response(400, "Dados de entrada inválidos")
    @api.response(404, "Opinião não encontrada")
    @api.response(500, "Erro interno do servidor")
    @api.doc(params={'tconst': 'ID do filme'})
    def put(self, tconst):
        """Atualiza a opinião pessoal de um filme específico"""
        data = request.get_json()
        if not data:
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
        return update_personal_opinion(
            tconst,
            data.get("opinion"),
            data.get("enjoying_1"),
            data.get("enjoying_2")
        )

    @api.doc("delete_personal_opinion")
    @api.response(200, "Opinião deletada com sucesso")
    @api.response(404, "Opinião não encontrada")
    @api.response(500, "Erro interno do servidor")
    def delete(self, tconst):
        """Deleta uma opinião pessoal específica"""
        opinion = get_personal_opinion(tconst)[0].get("data", {})
        if not opinion:
            return {"message": "Opinião não encontrada"}, 404
        return delete_personal_opinion(tconst, str(opinion["_id"]))

personal_opinion_bp.api = api
