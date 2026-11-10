import logging

import requests

from config import HTTP_TIMEOUT, OPEN_SUBTITLES_API_KEY, RAPIDAPI_API_KEY

logger = logging.getLogger(__name__)


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
        response = requests.get(search_url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.warning("Magnet link request for %s failed: %s", tconst, e)
        return None
    except ValueError as e:
        logger.warning("Magnet link response for %s is not JSON: %s", tconst, e)
        return None

    results = data.get("data") if isinstance(data, dict) else None
    if not isinstance(results, list) or not results:
        return None

    # The result with the most seeds wins.
    best_result = max(results, key=lambda item: int(item.get("seeds", 0) or 0))
    return best_result.get("magnet") or None


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
        response = requests.get(
            url, headers=headers, params=params, timeout=HTTP_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.warning("Subtitle request for %s failed: %s", tconst, e)
        return None
    except ValueError as e:
        logger.warning("Subtitle response for %s is not JSON: %s", tconst, e)
        return None

    results = data.get("data") if isinstance(data, dict) else None
    if not results:
        return None
    return results[0].get("attributes", {}).get("url") or None
