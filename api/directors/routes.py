from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields
from directors.controller import (
    add_director,
    get_favorited_directors,
    delete_favorited_director,
)
from urllib.parse import unquote
import os
import time

directors_bp = Blueprint("directors", __name__)
api = Namespace(
    "directors", description="Operações relacionadas aos diretores favoritos"
)

director_model = api.model(
    "DirectorInput",
    {"director": fields.String(required=True, description="Nome do diretor")},
)


@api.route("/")
class DirectorList(Resource):
    @api.doc("get_favorited_directors")
    @api.response(200, "Sucesso")
    def get(self):
        print("Requisição para recuperar diretores favoritos recebida")
        return get_favorited_directors()

    @api.doc("add_director")
    @api.expect(director_model)
    @api.response(201, "Diretor adicionado com sucesso")
    @api.response(409, "Diretor já está na lista")
    @api.response(400, "Diretor é obrigatório")
    def post(self):
        """Adiciona um diretor aos favoritos"""
        print("Requisição para adicionar diretor recebida")
        try:
            start_time = time.perf_counter()  # Início da medição de tempo
            request_data = request.get_json() or {}

            if not isinstance(request_data, dict) or "director" not in request_data:
                print("Diretor não fornecido no corpo da requisição")
                return {"data": "Director is required in request body"}, 400

            director = str(request_data["director"]).strip()
            if not director:
                print("Nome do diretor está vazio")
                return {"data": "Director cannot be empty"}, 400

            api_key = os.getenv("OPENAI_API_KEY")
            model = "gpt-4o"

            response, status_code = add_director(director, api_key, model)
            elapsed_time = time.perf_counter() - start_time  # Fim da medição de tempo
            print(f"Tempo para adicionar diretor: {elapsed_time:.2f} segundos")
            return response, status_code

        except Exception as e:
            print(f"Erro ao processar requisição: {e}")
            return {"data": "Invalid request format"}, 400


@api.route("/<string:director>")
class Director(Resource):
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
