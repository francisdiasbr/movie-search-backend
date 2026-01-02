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


# Função para buscar informações completas de uma playlist
def get_playlist_info(playlist_id):
    try:
        # Busca informações da playlist
        playlist = sp.playlist(playlist_id)
        
        # Busca todas as tracks da playlist
        tracks_data = []
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']
        
        # Paginação para buscar todas as músicas
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        
        # Processa as informações das tracks
        for item in tracks:
            if item['track']:
                track = item['track']
                track_info = {
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'album': track['album']['name'],
                    'duration_ms': track['duration_ms'],
                    'popularity': track.get('popularity'),
                    'uri': track['uri'],
                    'external_url': track['external_urls']['spotify'],
                    'preview_url': track.get('preview_url'),
                    'added_at': item.get('added_at')
                }
                tracks_data.append(track_info)
        
        # Monta o objeto de resposta completo
        playlist_info = {
            'id': playlist['id'],
            'name': playlist['name'],
            'description': playlist.get('description'),
            'owner': {
                'display_name': playlist['owner']['display_name'],
                'id': playlist['owner']['id']
            },
            'public': playlist.get('public'),
            'collaborative': playlist.get('collaborative'),
            'followers': playlist['followers']['total'],
            'external_url': playlist['external_urls']['spotify'],
            'total_tracks': playlist['tracks']['total'],
            'tracks': tracks_data
        }
        
        return playlist_info
        
    except Exception as e:
        return {"error": str(e)}
