from flask import Blueprint, request, jsonify
from flask_restx import Namespace, Resource, fields

from generate_review.controller import (
    create_and_save_movie_review,
    get_movie_review,
    get_generated_reviews
)

generate_review_bp = Blueprint("generate_review", __name__)
api = Namespace('generate-review', description='Operações relacionadas à geração de resenhas de filmes')

# Modelos para o Swagger
review_model = api.model('Review', {
    'tconst': fields.String(description='ID do filme'),
    'primaryTitle': fields.String(description='Título do filme'),
    'review': fields.String(description='Resenha gerada do filme'),
    'plot': fields.String(description='Enredo detalhado do filme')
})

review_search_model = api.model('ReviewSearch', {
    'filters': fields.Raw(description='Filtros para a busca'),
    'page': fields.Integer(description='Número da página', default=1),
    'page_size': fields.Integer(description='Tamanho da página', default=10)
})

review_list_response = api.model('ReviewListResponse', {
    'total_documents': fields.Integer(description='Total de documentos encontrados'),
    'entries': fields.List(fields.Nested(review_model))
})

@api.route('/<string:tconst>')
class MovieReview(Resource):
    @api.doc('get_movie_review')
    @api.response(200, 'Sucesso')
    @api.response(404, 'Resenha não encontrada')
    @api.response(500, 'Erro interno do servidor')
    @api.marshal_with(review_list_response)
    def get(self, tconst):
        """Recupera todas as resenhas e enredos de um filme favoritado"""
        return get_movie_review(tconst)

    @api.doc('create_movie_review')
    @api.response(200, 'Resenha criada com sucesso')
    @api.response(404, 'Filme não encontrado nos favoritos')
    @api.response(500, 'Erro interno do servidor')
    @api.marshal_with(review_model)
    def post(self, tconst):
        """Cria e salva a resenha e o enredo para um filme favoritado"""
        return create_and_save_movie_review(tconst)

@api.route('/search')
class GeneratedReviewSearch(Resource):
    @api.doc('search_generated_reviews')
    @api.expect(review_search_model)
    @api.response(200, 'Sucesso')
    @api.response(400, 'Dados de entrada inválidos')
    @api.response(500, 'Erro interno do servidor')
    @api.marshal_with(review_list_response)
    def post(self):
        """Pesquisa resenhas e enredos gerados"""
        request_data = request.get_json()
        if not isinstance(request_data, dict):
            return {"status": 400, "message": "Invalid input data"}, 400
        return get_generated_reviews(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 10),
        )

generate_review_bp.api = api