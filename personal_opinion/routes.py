from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields
from .controller import insert_personal_opinion, get_personal_opinions

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

personal_opinion_bp.api = api
