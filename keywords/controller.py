import logging

import db
from config import KEYWORDS_COLLECTION, get_mongo_collection
from keywords.imdb import (
    IMDBSearchError,
    search_movies_by_director,
    search_movies_by_keyword,
)
from utils import error

logger = logging.getLogger(__name__)


def keywords():
    return get_mongo_collection(KEYWORDS_COLLECTION)


def add_keyword(keyword):
    keyword = str(keyword or "").strip()
    if not keyword:
        return error("Keyword is required", 400)

    collection = keywords()
    if collection.find_one({"keyword": keyword}):
        return error("Keyword already listed", 409)

    return {"data": db.insert(collection, {"keyword": keyword})}, 201


def get_favorited_keywords():
    _, entries = db.search(keywords(), projection={"keyword": 1}, sort=("keyword", 1))
    return {"data": entries}, 200


def delete_favorited_keyword(keyword):
    if not db.delete(keywords(), {"keyword": keyword}):
        return error("Keyword not found", 404)
    return {"data": "Keyword deleted successfully"}, 200


# Movies asked to IMDB per keyword; the answer keeps the best SUGGESTION_LIMIT.
PER_KEYWORD = 15
SUGGESTION_LIMIT = 15


def suggest_movies_by_keywords(keywords):
    """Movies IMDB tags with the keywords, the ones matching more first.

    One IMDB search per keyword; a keyword that is a director's name
    ("François Truffaut") brings the movies they directed instead. A movie
    that comes back for several keywords ranks above one that matches a
    single keyword, and within the same count IMDB's order is kept. A keyword IMDB does not know
    simply contributes nothing; the answer is 502 only when every search
    failed.
    """
    matches = {}
    failures = 0
    for keyword in dict.fromkeys(str(k).strip() for k in keywords if str(k).strip()):
        try:
            movies = search_movies_by_director(
                keyword, PER_KEYWORD
            ) or search_movies_by_keyword(keyword, PER_KEYWORD)
        except IMDBSearchError as e:
            logger.error("%s", e)
            failures += 1
            continue
        for rank, movie in enumerate(movies):
            entry = matches.setdefault(
                movie["tconst"], {"movie": movie, "keywords": [], "rank": rank}
            )
            entry["keywords"].append(keyword)

    if not matches and failures:
        return error("Falha ao buscar filmes no IMDb", 502)

    ranked = sorted(matches.values(), key=lambda e: (-len(e["keywords"]), e["rank"]))
    suggestions = [
        {
            **entry["movie"],
            "relevance": "Palavras-chave no IMDb: " + ", ".join(entry["keywords"]),
        }
        for entry in ranked[:SUGGESTION_LIMIT]
    ]
    return {"data": {"movies": suggestions}}, 200
