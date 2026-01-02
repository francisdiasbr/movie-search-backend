from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields
from .controller import get_album_by_movie_title, get_playlist_info

spotify_bp = Blueprint("spotify", __name__)
api = Namespace(
    "spotify",
    description="Operações relacionadas a trilhas sonoras de filmes",
)

# Modelo para o Swagger
soundtrack_request_model = api.model(
    "SoundtrackRequest",
    {
        "title": fields.String(required=True, description="Título do filme"),
    },
)

soundtrack_response_model = api.model(
    "SoundtrackResponse",
    {
        "data": fields.String(description="URL do álbum no Spotify"),
    },
)

@api.route("/soundtrack")
class Soundtrack(Resource):
    @api.doc("get_album_by_movie_title")
    @api.expect(soundtrack_request_model)
    @api.response(200, "Sucesso", soundtrack_response_model)
    def post(self):
        """Busca o álbum da trilha sonora de um filme no Spotify"""
        data = request.get_json()
        title = data.get("title")
        
        if not title:
            return {"data": "title is required"}, 400
            
        album_url = get_album_by_movie_title(title)
        return {"data": album_url}


@api.route("/playlist/<string:playlist_id>")
class Playlist(Resource):
    @api.doc("get_playlist_info")
    @api.response(200, "Sucesso")
    @api.response(400, "Erro ao buscar playlist")
    def get(self, playlist_id):
        """Busca informações completas de uma playlist do Spotify"""
        if not playlist_id:
            return {"error": "playlist_id is required"}, 400
            
        playlist_info = get_playlist_info(playlist_id)
        
        if "error" in playlist_info:
            return playlist_info, 400
            
        return playlist_info, 200

spotify_bp.api = api 