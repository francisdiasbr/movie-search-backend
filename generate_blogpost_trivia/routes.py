from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields


from config import OPENAI_API_KEY
from generate_blogpost_trivia.controller import (
    create_and_save_blog_post_trivia,
    get_blog_post_trivia,
    get_blogposts_trivia,
    update_blog_post_trivia
)

generate_blogpost_trivia_bp = Blueprint("generate_blogpost_trivia", __name__)
api = Namespace(
    "generate-blogpost-trivia",
    description="Operações relacionadas à geração de trívia de postagens de blog sobre filmes"
)
# Modelos para o Swagger
blog_post_trivia_model = api.model(
    "BlogPostTrivia",
    {
        "data": fields.Nested(api.model("BlogPostTriviaData", {
            "tconst": fields.String(description="Identificador único do filme"),
            "primaryTitle": fields.String(description="Título principal do filme"),
            "director_history": fields.String(description="História do diretor e relação do filme com ele"),
            "director_quotes": fields.String(description="Citações. Extraia do IMDb"),
            "curiosities": fields.String(description="Curiosidades sobre o filme"),
            "reception": fields.String(description="Recepção do filme"),
            "highlights": fields.String(description="Destaques do filme. Fale sobre os pontos fortes do filme e em como ele ficou conhecido"),
            "plot": fields.String(description="Enredo do filme"),
        }))
    }
)

blog_search_model = api.model(
    "BlogSearch",
    {
        "filters": fields.Raw(description="Filtros para a busca"),
        "page": fields.Integer(description="Número da página", default=1),
        "page_size": fields.Integer(description="Tamanho da página", default=10)
    }
)

blog_list_response = api.model(
    "BlogListResponse",
    {
        "total_documents": fields.Integer(description="Total de documentos encontrados"),
        "entries": fields.List(fields.Nested(blog_post_trivia_model))
    }
)

@api.route("/<string:tconst>")
class MovieBlogPostTrivia(Resource):
    @api.doc("get_blog_post_trivia")
    @api.response(200, "Sucesso")
    @api.response(404, "Postagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    @api.marshal_with(blog_post_trivia_model)
    def get(self, tconst):
        """Recupera a postagem do blog para um filme específico"""
        return get_blog_post_trivia(tconst)

    @api.doc("create_blog_post_trivia")
    @api.response(200, "Postagem criada com sucesso")
    @api.response(404, "Filme não encontrado nos favoritos")
    @api.response(500, "Erro interno do servidor")
    @api.marshal_with(blog_post_trivia_model)
    def post(self, tconst):
        """Cria e salva uma postagem de blog para um filme favoritado"""
        model = "gpt-4o"
        return create_and_save_blog_post_trivia(tconst, OPENAI_API_KEY, model)

    @api.doc("update_blog_post_trivia")
    @api.response(200, "Postagem atualizada com sucesso")
    @api.response(404, "Postagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def put(self, tconst):
        """Atualiza uma postagem de blog existente"""
        data = request.get_json()
        return update_blog_post_trivia(tconst, data)

@api.route("/search")
class BlogPostSearchTrivia(Resource):
    @api.doc("search_blog_posts_trivia")
    @api.expect(blog_search_model)
    @api.response(200, "Sucesso")
    @api.response(400, "Dados de entrada inválidos")
    def post(self):
        """Pesquisa postagens de blog"""
        request_data = request.get_json()
        if not isinstance(request_data, dict):
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
            
        return get_blogposts_trivia(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 10)
        )

generate_blogpost_trivia_bp.api = api 