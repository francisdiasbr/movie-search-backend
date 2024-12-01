from flask import Blueprint, jsonify, request
from flask_restx import Namespace, Resource, fields

from write_review.controller import (
    create_and_save_movie_review,
    delete_movie_review,
    edit_movie_review,
    get_movie_review,
    get_created_reviews
)

write_review_bp = Blueprint("write_review", __name__)

api = Namespace('write-review', description='Operações relacionadas a resenhas escritas')
write_review_bp.api = api


review_input = api.model('ReviewInput', {
    'data': fields.Nested(api.model('ReviewData', {
        'author': fields.String(required=True, description='Autor da resenha'),
        'reviewTitle': fields.String(required=True, description='Título da resenha'),
        'review': fields.String(required=True, description='Conteúdo da resenha')
    }))
})

review_output = api.model('ReviewOutput', {
    'data': fields.Nested(api.model('ReviewDocument', {
        '_id': fields.String(description='ID da resenha'),
        'tconst': fields.String(description='ID do filme'),
        'reviewTitle': fields.String(description='Título da resenha'),
        'review': fields.String(description='Conteúdo da resenha'),
        'author': fields.String(description='Autor da resenha')
    }))
})

search_input = api.model('SearchInput', {
    'filters': fields.Raw(description='Filtros de busca', default={}),
    'page': fields.Integer(description='Número da página', default=1),
    'page_size': fields.Integer(description='Tamanho da página', default=10)
})

@api.route('/<string:tconst>')
class MovieReview(Resource):
    @api.doc('get_review')
    @api.response(200, 'Success', review_output)
    @api.response(404, 'Review not found')
    def get(self, tconst):
        """Obtém todas as resenhas de um filme específico"""
        return get_movie_review(tconst)

    @api.doc('create_review')
    @api.expect(review_input)
    @api.response(200, 'Success', review_output)
    @api.response(404, 'Movie not found')
    def post(self, tconst):
        """Cria uma nova resenha para um filme"""
        return create_and_save_movie_review(tconst)

    @api.doc('update_review')
    @api.expect(review_input)
    @api.response(200, 'Success')
    @api.response(404, 'Review not found')
    def put(self, tconst):
        """Atualiza uma resenha existente"""
        request_data = request.get_json().get("data", {})
        return edit_movie_review(
            tconst,
            request_data.get("reviewTitle"),
            request_data.get("author"),
            request_data.get("review")
        )

@api.route('/<string:tconst>/<string:review_id>')
class MovieReviewDetail(Resource):
    @api.doc('update_review')
    @api.expect(review_input)
    @api.response(200, 'Success')
    @api.response(404, 'Review not found')
    def put(self, tconst, review_id):
        """Atualiza uma resenha específica"""
        request_data = request.get_json().get("data", {})
        return edit_movie_review(
            tconst,
            review_id,
            request_data.get("reviewTitle"),
            request_data.get("author"),
            request_data.get("review")
        )

    @api.doc('delete_review')
    @api.response(200, 'Review deleted')
    @api.response(404, 'Review not found')
    def delete(self, tconst, review_id):
        """Remove uma resenha específica"""
        return delete_movie_review(tconst, review_id)

@api.route('/search')
class ReviewSearch(Resource):
    @api.doc('search_reviews')
    @api.expect(search_input)
    @api.response(200, 'Success')
    @api.response(400, 'Invalid input data')
    def post(self):
        """Busca resenhas com filtros"""
        request_data = request.get_json() or {}
        
        return get_created_reviews(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 10),
        )