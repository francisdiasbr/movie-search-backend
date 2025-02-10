from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields
from urllib.parse import unquote
import time

from directors.controller import (
    add_director,
    get_favorited_directors,
    delete_favorited_director,
    get_director_details,
)
from config import OPENAI_API_KEY

directors_bp = Blueprint("directors", __name__)
api = Namespace(
    "directors", description="Operações relacionadas aos diretores favoritos"
)

director_model = api.model(
    "DirectorInput",
    {"director": fields.String(required=True, description="Nome do diretor")},
)

# Rotas para recuperar a lista de diretores favoritos e adicionar diretores aos favoritos
@api.route("/")
class DirectorList(Resource):
    # Rota para recuperar a lista de diretores favoritos
    @api.doc("get_favorited_directors")
    @api.response(200, "Sucesso")
    
    def get(self):
        print("Requisição para recuperar diretores favoritos recebida")
        return get_favorited_directors()

    # Rota para adicionar um diretor aos favoritos
    @api.doc("add_director")
    @api.expect(director_model)
    @api.response(201, "Diretor adicionado com sucesso")
    @api.response(409, "Diretor já está na lista")
    @api.response(400, "Diretor é obrigatório")
    def post(self):
        """Adiciona um diretor aos favoritos"""
        print("Requisição para adicionar diretor recebida")
        try:
            start_time = time.perf_counter()
            request_data = request.get_json() or {}

            if not isinstance(request_data, dict) or "director" not in request_data:
                return {"data": "Director is required in request body"}, 400

            director = str(request_data["director"]).strip()
            if not director:
                return {"data": "Director cannot be empty"}, 400

            api_key = OPENAI_API_KEY
            model = "gpt-4"

            response, status_code = add_director(director, api_key, model)
            
            elapsed_time = time.perf_counter() - start_time
            print(f"Tempo para adicionar diretor: {elapsed_time:.2f} segundos")
            return response, status_code

        except Exception as e:
            print(f"Erro ao processar requisição: {str(e)}")
            return {"data": f"Error processing request: {str(e)}"}, 500

# Rotas para recuperar e deletardetalhes do diretor    
@api.route("/<string:director>")
class Director(Resource):
    # Rota para recuperar detalhes do diretor
    @api.doc("get_director_details")
    @api.response(200, "Sucesso")
    @api.response(404, "Diretor não encontrado")
    def get(self, director):
        """Recupera todas as propriedades de um diretor específico"""
        # Decodifica o nome do diretor para lidar com espaços e caracteres especiais
        decoded_director = unquote(director)
        print(f"Requisição para recuperar detalhes do diretor: {decoded_director}")
        return get_director_details(decoded_director)

    # Rota para remover um diretor dos favoritos
    @api.doc("delete_favorite_director")
    @api.response(200, "Diretor removido com sucesso")
    @api.response(404, "Diretor não encontrado")
    def delete(self, director):
        """Remove um diretor dos favoritos"""
        # Decodifica o nome do diretor para lidar com espaços e caracteres especiais
        decoded_director = unquote(director)
        print(f"Requisição para remover diretor: {decoded_director}")
        return delete_favorited_director(decoded_director)


directors_bp.api = api
