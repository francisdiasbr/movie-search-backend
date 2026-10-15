import logging
from datetime import datetime

import db
from config import BLOGPOSTS_COLLECTION, FAVORITES_COLLECTION, get_mongo_collection

from favorites.scrapper import (
    clear_soup_cache,
    get_director,
    get_movie_country,
    get_movie_genres,
    get_movie_plot_keywords,
    get_movie_poster,
    get_movie_principal_stars,
    get_movie_quote,
    get_movie_sm_plot,
    get_movie_title,
    get_movie_trivia,
    get_movie_year,
    get_wikipedia_url,
    get_writers,
)
from utils import error, pick
from favorites.external_requests import get_magnet_link, get_subtitle_url

logger = logging.getLogger(__name__)

# Scrapers that take a tconst, keyed by the field each one fills in. Adding a
# new field to a favorite means adding one entry here.
SCRAPERS = {
    "country": get_movie_country,
    "director": get_director,
    "genres": get_movie_genres,
    "magnet_link": get_magnet_link,
    "plot": get_movie_sm_plot,
    "plot_keywords": get_movie_plot_keywords,
    "poster_url": get_movie_poster,
    "quote": get_movie_quote,
    "stars": get_movie_principal_stars,
    "startYear": get_movie_year,
    "subtitle_url": get_subtitle_url,
    "trivia": get_movie_trivia,
    "writers": get_writers,
}


def collect_movie_data(tconst, title):
    """Runs every scraper, keeping only the fields that resolved.

    Sequential on purpose. Every IMDB page load is serialized by the browser
    thread anyway, and running the scrapers concurrently made them all miss the
    soup cache at once and queue the same URL again - 7 page loads instead of 4,
    and twice the wall clock.
    """
    data = {}
    # The only scraper keyed by title instead of tconst.
    scrapers = {**SCRAPERS, "wiki": lambda _: get_wikipedia_url(title)}

    for field, scraper in scrapers.items():
        try:
            value = scraper(tconst)
            if value is not None and value != "":
                data[field] = value
        except Exception as e:
            logger.warning("Could not fetch %s for %s: %s", field, tconst, e)

    # Every scraper is done with the IMDB pages by now.
    clear_soup_cache()
    return data


def favorite_movie(tconst):
    collection = get_mongo_collection(FAVORITES_COLLECTION)
    if collection.find_one({"tconst": tconst}):
        return error("Movie already listed", 409)

    title = get_movie_title(tconst)
    if not title:
        logger.warning("Title for %s not found on IMDB", tconst)
        return error("Título do filme não encontrado no IMDB", 404)

    movie = db.insert(
        collection,
        {
            "primaryTitle": title,
            "tconst": tconst,
            "imdb_url": f"https://www.imdb.com/title/{tconst}/",
            "created_at": datetime.now().isoformat(),
            "references": [],
            **collect_movie_data(tconst, title),
        },
    )
    logger.info("Movie %s added as %s", tconst, movie["_id"])
    return {"data": movie}, 201


def get_favorited_movie(tconst):
    movie = db.serialize(get_mongo_collection(FAVORITES_COLLECTION).find_one({"tconst": tconst}))
    if not movie:
        return error("Movie not found", 404)
    return {"data": movie}, 200


# Fields the client may change on a favorite.
EDITABLE_FIELDS = ("magnet_link", "references", "soundtrack", "watched", "wiki")

# Fields mirrored onto the blogpost of the same movie, when one exists.
BLOGPOST_MIRROR = {
    "references": "references",
    "soundtrack": "spotify_album_url",
}


def sync_blogpost(tconst, update_data):
    """Mirrors the edited fields onto the movie's blogpost, if it has one."""
    mirrored = {
        blogpost_field: update_data[field]
        for field, blogpost_field in BLOGPOST_MIRROR.items()
        if field in update_data
    }
    if not mirrored:
        return

    try:
        collection = get_mongo_collection(BLOGPOSTS_COLLECTION)
        if collection.find_one({"tconst": tconst}):
            collection.update_one({"tconst": tconst}, {"$set": mirrored})
            logger.info("Blogpost of %s synced with %s", tconst, sorted(mirrored))
    except Exception as e:
        logger.error("Could not sync blogpost of %s: %s", tconst, e)


def edit_favorited_movie(tconst, request_data):
    """Updates only the fields present in the body; the others are kept."""
    fields = pick(request_data, EDITABLE_FIELDS)
    movie = db.update(get_mongo_collection(FAVORITES_COLLECTION), {"tconst": tconst}, fields)
    if not movie:
        return error(f"Movie {tconst} not found", 404)

    sync_blogpost(tconst, fields)
    return {"data": movie}, 200


def delete_favorited_movie(tconst):
    if not db.delete(get_mongo_collection(FAVORITES_COLLECTION), {"tconst": tconst}):
        return error(f"Movie {tconst} not found", 404)
    return {"data": f"Movie {tconst} deleted"}, 200


# Campos que a listagem do frontend realmente usa. O documento completo carrega
# trivia, quote, plot e plot_keywords, que só fazem sentido na tela de detalhe -
# essa busca o filme inteiro pelo GET /favorites/<tconst>.
LIST_PROJECTION = {
    "poster_url": 1,
    "primaryTitle": 1,
    "tconst": 1,
    "watched": 1,
}


def get_favorited_movies(filters=None, page=1, page_size=0, search_term=""):
    collection = get_mongo_collection(FAVORITES_COLLECTION)

    # Copied so the caller's dict (the request body) is never mutated.
    filters = dict(filters or {})
    search_term = search_term or filters.pop("search_term", None) or filters.get("tconst")

    # `search_term` matches the exact tconst or part of the title/director.
    if search_term:
        term = str(search_term)
        filters["$or"] = [
            {"tconst": term},
            {"primaryTitle": {"$regex": term, "$options": "i"}},
            {"director": {"$regex": term, "$options": "i"}},
        ]

    total, entries = db.search(
        collection, filters, projection=LIST_PROJECTION, page=page, page_size=page_size
    )
    return {
        "total_documents": total,
        "entries": entries,
        "countries": collection.distinct("country"),
        "years": [
            int(year)
            for year in collection.distinct("startYear")
            if year is not None and str(year).isdigit()
        ],
    }, 200
