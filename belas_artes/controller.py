import logging
import time
from concurrent.futures import ThreadPoolExecutor

from belas_artes.catalog import CatalogUnavailable, load_catalog, view_titles
from keywords.imdb import IMDBSearchError, find_rating
from utils import error

logger = logging.getLogger(__name__)

RECENT_VIEW = "adicionados-recentemente"

# A rating barely moves in a day; caching avoids ~50 IMDB searches per page load.
RATING_TTL = 24 * 60 * 60
RATING_WORKERS = 8
_ratings = {}


def _rating(title, year):
    """IMDB match of a title, cached; None when IMDB has no match or fails."""
    key = (title, year)
    cached = _ratings.get(key)
    if cached and time.time() - cached["at"] < RATING_TTL:
        return cached["match"]

    try:
        match = find_rating(title, year)
    except IMDBSearchError as e:
        # Not cached, so the next load tries again.
        logger.error("%s", e)
        return None

    _ratings[key] = {"match": match, "at": time.time()}
    return match


def get_recently_added():
    """Movies of the "Adicionados recentemente" section, with the IMDB rating."""
    try:
        titles = view_titles(load_catalog(), RECENT_VIEW)
    except CatalogUnavailable as e:
        logger.error("%s", e)
        return error("Falha ao buscar o catálogo do Belas Artes", 502)

    if titles is None:
        return error("Seção de adicionados recentemente não encontrada", 404)

    with ThreadPoolExecutor(RATING_WORKERS) as pool:
        matches = list(
            pool.map(
                lambda t: _rating(t["original_title"] or t["title"], t["year"]),
                titles,
            )
        )

    movies = [
        {
            "id": title["id"],
            "title": title["title"].strip(),
            "original_title": title["original_title"].strip(),
            "year": title["year"],
            "director": title["director"].strip(),
            "tconst": (match or {}).get("tconst"),
            "imdb_rating": (match or {}).get("rating"),
        }
        for title, match in zip(titles, matches)
    ]
    return {"data": {"movies": movies}}, 200
