from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields


from config import OPENAI_API_KEY
from generate_blogpost.controller import (
    create_and_save_blog_post,
    get_blog_post,
    get_blogposts,
    update_blog_post
)

generate_blogpost_bp = Blueprint("generate_blogpost", __name__)
api = Namespace(
    "generate-blogpost",
    description="Operações relacionadas à geração de postagens de blog sobre filmes"
)

# Modelos para o Swagger
blog_post_model = api.model(
    "BlogPost",
    {
        "data": fields.Nested(api.model("BlogPostData", {
            "tconst": fields.String(description="ID do filme"),
            "primaryTitle": fields.String(description="Título do filme"),
            "title": fields.String(description="Título da postagem"),
            "introduction": fields.String(description="Introdução da postagem"),
            "stars_and_characters": fields.String(description="Principais estrelas e personagens do filme"),
            "historical_context": fields.String(description="Contexto histórico"),
            "cultural_importance": fields.String(description="Importância cultural"),
            "technical_analysis": fields.String(description="Análise técnica"),
            "conclusion": fields.String(description="Conclusão"),
            "original_movie_soundtrack": fields.String(description="Trilha sonora original do filme"),
            "poster_url": fields.String(description="URL do pôster do filme"),
            "created_at": fields.String(description="Timestamp da criação da postagem"),
            "references": fields.List(fields.String, description="Links relacionados com a postagem"),
            "soundtrack_video_url": fields.String(description="URL do vídeo da trilha sonora no YouTube")
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
        "entries": fields.List(fields.Nested(blog_post_model))
    }
)

@api.route("/<string:tconst>")
class MovieBlogPost(Resource):
    @api.doc("get_blog_post")
    @api.response(200, "Sucesso")
    @api.response(404, "Postagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    @api.marshal_with(blog_post_model)
    def get(self, tconst):
        """Recupera a postagem do blog para um filme específico"""
        return get_blog_post(tconst)

    @api.doc("create_blog_post")
    @api.response(200, "Postagem criada com sucesso")
    @api.response(404, "Filme não encontrado nos favoritos")
    @api.response(500, "Erro interno do servidor")
    @api.marshal_with(blog_post_model)
    def post(self, tconst):
        """Cria e salva uma postagem de blog para um filme favoritado"""
        model = "gpt-4o"
        return create_and_save_blog_post(tconst, OPENAI_API_KEY, model)

    @api.doc("update_blog_post")
    @api.response(200, "Postagem atualizada com sucesso")
    @api.response(404, "Postagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def put(self, tconst):
        """Atualiza uma postagem de blog existente"""
        data = request.get_json()
        return update_blog_post(tconst, data)

@api.route("/search")
class BlogPostSearch(Resource):
    @api.doc("search_blog_posts")
    @api.expect(blog_search_model)
    @api.response(200, "Sucesso")
    @api.response(400, "Dados de entrada inválidos")
    def post(self):
        """Pesquisa postagens de blog"""
        request_data = request.get_json()
        if not isinstance(request_data, dict):
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
            
        return get_blogposts(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 10)
        )

generate_blogpost_bp.api = api 