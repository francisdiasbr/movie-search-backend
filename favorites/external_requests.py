import requests
from config import RAPIDAPI_API_KEY, OPEN_SUBTITLES_API_KEY
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_magnet_link(tconst):
    search_url = f"https://movie_torrent_api1.p.rapidapi.com/search/{tconst}"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-rapidapi-ua": "RapidAPI-Playground",
        "x-rapidapi-key": RAPIDAPI_API_KEY,
        "x-rapidapi-host": "movie_torrent_api1.p.rapidapi.com",
    }

    try:
        response = requests.get(search_url, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()

        # Verifica se há dados na resposta e se é uma lista não vazia
        if data and isinstance(data.get("data"), list) and data["data"]:
            # Ordena os resultados por número de seeds (mais seeds primeiro)
            sorted_results = sorted(
                data["data"], key=lambda x: int(x.get("seeds", 0)), reverse=True
            )

            # Pega o primeiro resultado (com mais seeds)
            best_result = sorted_results[0]
            magnet_link = best_result.get("magnet")

            if magnet_link:
                return magnet_link

        return None

    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return None
    except ValueError as e:
        print(f"JSON parsing error: {str(e)}")
        return None


def get_subtitle_url(tconst):
    url = "https://api.opensubtitles.com/api/v1/subtitles"

    headers = {
        "Api-Key": OPEN_SUBTITLES_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "Movie-Search-API/1.0",
    }

    params = {
        "imdb_id": tconst.replace("tt", ""),  # A API espera o ID sem o prefixo "tt"
        "languages": "en",
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        if data and "data" in data and len(data["data"]) > 0:
            # Pega a URL do primeiro resultado
            first_subtitle = data["data"][0]
            subtitle_url = first_subtitle.get("attributes", {}).get("url")
            return subtitle_url

        return None

    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return None
    except ValueError as e:
        print(f"JSON parsing error: {str(e)}")
        return None
