"""Resolves a movie suggested by the model to a real IMDB title.

The model guesses the tconst and gets it wrong often, so the id is never
trusted: the title and year are looked up in IMDB's public suggestion API
(the one behind the search box, no session or scraping needed) and the match
decides whether the suggestion is kept.
"""

import logging
import re
import unicodedata
from urllib.parse import quote

import requests

from config import HTTP_TIMEOUT

logger = logging.getLogger(__name__)

SUGGESTION_API = "https://v3.sg.media-imdb.com/suggestion/x/{query}.json"
MOVIE_TYPES = {"feature", "tv movie", "short", "tv series", "tv mini series", "video"}
# IMDB lists the festival year; the model often answers the release year.
YEAR_TOLERANCE = 1


def _normalize(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _search(query):
    url = SUGGESTION_API.format(query=quote(_normalize(query)))
    try:
        response = requests.get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.warning("IMDB suggestion search failed for %r: %s", query, e)
        return []
    try:
        return response.json().get("d", [])
    except ValueError:
        logger.warning("IMDB suggestion search returned a non-JSON body for %r", query)
        return []


def find_imdb_title(title, year, original_title=None):
    """Returns {"tconst", "title", "year"} of the IMDB title matching the
    suggestion, or None when IMDB does not know it.

    A candidate must be a title (not a person), be a movie-like type and sit
    within YEAR_TOLERANCE of the suggested year. Among those, an exact
    (normalized) title match wins; otherwise the first one is taken, since
    the API already ranks by relevance.
    """
    wanted = {_normalize(title)}
    if original_title:
        wanted.add(_normalize(original_title))

    candidates = []
    for query in dict.fromkeys([original_title, title]):
        if not query:
            continue
        for item in _search(query):
            tconst = item.get("id", "")
            item_year = item.get("y")
            if not tconst.startswith("tt") or item.get("q") not in MOVIE_TYPES:
                continue
            if item_year is None or abs(int(item_year) - int(year)) > YEAR_TOLERANCE:
                continue
            candidates.append(item)
        if candidates:
            break

    if not candidates:
        return None

    exact = [item for item in candidates if _normalize(item.get("l")) in wanted]
    match = (exact or candidates)[0]
    return {"tconst": match["id"], "title": match.get("l") or title, "year": match.get("y")}
