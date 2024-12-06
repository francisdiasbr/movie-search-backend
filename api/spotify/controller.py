import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

# Configuração das credenciais
client_id = SPOTIFY_CLIENT_ID
client_secret = SPOTIFY_CLIENT_SECRET
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


# Função para buscar um album pelo nome do filme
def get_album_by_movie_title(movie_title):
    query = f"{movie_title} Soundtrack"
    results = sp.search(q=query, type="album", limit=1)
    if results["albums"]["items"]:
        album_url = results["albums"]["items"][0]["external_urls"]["spotify"]
        return album_url
    else:
        return "No album found"
