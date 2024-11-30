from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from movies.controller import get_movies

movies_bp = Blueprint("movies", __name__)
api = Namespace('movies', description='Busca de filmes na base de dados')

# Definição dos modelos para o Swagger
movie_filter_model = api.model('MovieFilter', {
    'filters': fields.Raw(description='Filtros para a busca'),
    'page': fields.Integer(description='Número da página', default=1),
    'page_size': fields.Integer(description='Tamanho da página', default=10),
    'search_term': fields.String(description='Termo de busca', default='')
})

movie_response = api.model('MovieResponse', {
    'total_documents': fields.Integer(description='Total de documentos encontrados'),
    'entries': fields.List(fields.Raw(description='Lista de filmes'))
})

@api.route('/search')
class MovieSearch(Resource):
    @api.doc('search_movies')
    @api.expect(movie_filter_model)
    @api.response(200, 'Sucesso', movie_response)
    @api.response(500, 'Erro interno do servidor')
    def post(self):
        """Pesquisa os filmes na base de dados"""
        request_data = request.get_json()
        return get_movies(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 10),
            search_term=request_data.get("search_term", "")
        )

movies_bp.api = api
