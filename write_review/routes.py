from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from write_review.controller import (
    create_and_save_movie_review,
    delete_movie_review,
    edit_movie_review,
    get_movie_review,
    get_created_reviews,
)

write_review_bp = Blueprint("write_review", __name__)

api = Namespace(
    "write-review", description="Operações relacionadas a resenhas escritas"
)
write_review_bp.api = api


def unwrap(body):
    """Accepts the review fields at the top level or inside a `data` envelope.

    The frontend sends them at the top level; older clients wrapped them.
    """
    if not isinstance(body, dict):
        return {}
    data = body.get("data")
    return data if isinstance(data, dict) else body


# Modelos para o Swagger
review_content_model = api.model(
    "ReviewContent", {"text": fields.String(description="Texto da resenha")}
)

review_content_languages = api.model(
    "ReviewContentLanguages",
    {
        "en": fields.Nested(review_content_model),
        "pt": fields.Nested(review_content_model),
    },
)

# The body is the review itself, without a `data` envelope. The `pt` text is
# the only required part; `en` is optional.
review_input = api.model(
    "ReviewInput",
    {
        "content": fields.Nested(review_content_languages, required=True),
        "references": fields.List(fields.String, description="Lista de referências"),
        "images": fields.List(fields.String, description="Lista de URLs de imagens"),
        "isAiGenerated": fields.Boolean(description="Resenha gerada por IA"),
    },
)

review_update_input = api.model(
    "ReviewUpdateInput",
    {
        "content": fields.Nested(review_content_languages),
        "references": fields.List(fields.String),
        "images": fields.List(fields.String),
    },
)

review_output = api.model(
    "ReviewOutput",
    {
        "data": fields.Nested(
            api.model(
                "ReviewDocument",
                {
                    "tconst": fields.String(description="ID do filme"),
                    "primaryTitle": fields.String(description="Título do filme"),
                    "content": fields.Nested(
                        api.model(
                            "ReviewContentOutput",
                            {
                                "en": fields.Nested(review_content_model),
                                "pt": fields.Nested(review_content_model),
                            },
                        )
                    ),
                    "created_at": fields.String(description="Data de criação"),
                    "isAiGenerated": fields.Boolean(
                        description="Indica se a resenha foi gerada por IA"
                    ),
                    "references": fields.List(fields.String),
                    "images": fields.List(fields.String),
                },
            )
        )
    },
)

search_input = api.model(
    "SearchInput",
    {
        "filters": fields.Raw(description="Filtros de busca", default={}),
        "page": fields.Integer(description="Número da página", default=1),
        "page_size": fields.Integer(description="Tamanho da página", default=10),
    },
)


@api.route("/<string:tconst>")
class MovieReview(Resource):
    @api.doc("get_review")
    @api.response(200, "Success", review_output)
    @api.response(404, "Review not found")
    def get(self, tconst):
        """Obtém a resenha de um filme específico"""
        return get_movie_review(tconst)

    @api.doc("create_review")
    @api.expect(review_input)
    @api.response(201, "Created", review_output)
    @api.response(404, "Movie not found")
    @api.response(409, "Review already exists")
    def post(self, tconst):
        """Cria uma nova resenha para um filme"""
        return create_and_save_movie_review(tconst, unwrap(request.get_json()))

    @api.doc("update_review")
    @api.expect(review_update_input)
    @api.response(200, "Success")
    @api.response(404, "Review not found")
    def put(self, tconst):
        """Atualiza a resenha de um filme específico"""
        return edit_movie_review(tconst, unwrap(request.get_json()))

    @api.doc("delete_review")
    @api.response(200, "Review deleted")
    @api.response(404, "Review not found")
    def delete(self, tconst):
        """Remove a resenha de um filme específico"""
        return delete_movie_review(tconst)


@api.route("/search")
class ReviewSearch(Resource):
    @api.doc("search_reviews")
    @api.expect(search_input)
    @api.response(200, "Success")
    @api.response(400, "Invalid input data")
    def post(self):
        """Busca resenhas com filtros"""
        request_data = request.get_json() or {}

        return get_created_reviews(
            filters=request_data.get("filters", {}),
        )
