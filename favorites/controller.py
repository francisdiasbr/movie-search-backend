import logging
from datetime import datetime

from pymongo import ReturnDocument

from config import get_mongo_collection

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
from utils import sanitize_movie_data, sanitize_filters
from favorites.external_requests import get_magnet_link, get_subtitle_url

logger = logging.getLogger(__name__)

COLLECTION = "favoritelist"

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
    if not tconst:
        return {"data": "tconst is required"}, 400

    collection = get_mongo_collection(COLLECTION)
    if collection.find_one({"tconst": tconst}):
        return {"data": "Movie already listed"}, 409

    title = get_movie_title(tconst)
    if not title:
        logger.warning("Title for %s not found on IMDB", tconst)
        return {"data": "Título do filme não encontrado no IMDB"}, 404

    movie_data = {
        "primaryTitle": title,
        "tconst": tconst,
        "imdb_url": f"https://www.imdb.com/title/{tconst}/",
        "created_at": datetime.now().isoformat(),
        "references": [],
        **collect_movie_data(tconst, title),
    }

    try:
        movie_data["_id"] = str(collection.insert_one(movie_data).inserted_id)
        logger.info("Movie %s added as %s", tconst, movie_data["_id"])
        return {"data": movie_data}, 201
    except Exception as e:
        logger.error("Could not insert %s: %s", tconst, e)
        return {"status": 500, "message": "Erro ao inserir filme"}, 500


# Recupera um filme favoritado
def get_favorited_movie(tconst):
    if not tconst:
        return {"data": "tconst is required"}, 400

    collection = get_mongo_collection(COLLECTION)
    try:
        movie = collection.find_one({"tconst": tconst})
        if movie:
            movie["_id"] = str(movie["_id"])
            return {"data": movie}, 200
        else:
            return {"data": "Movie not found"}, 404
    except Exception as e:
        logger.error("Could not fetch %s: %s", tconst, e)
        return {"data": "Failed to retrieve movie"}, 500


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
        collection = get_mongo_collection("blogposts")
        if collection.find_one({"tconst": tconst}):
            collection.update_one({"tconst": tconst}, {"$set": mirrored})
            logger.info("Blogpost of %s synced with %s", tconst, sorted(mirrored))
    except Exception as e:
        logger.error("Could not sync blogpost of %s: %s", tconst, e)


# Edita um filme favoritado
def edit_favorited_movie(tconst, soundtrack=None, wiki=None, watched=None, references=None, magnet_link=None):
    collection = get_mongo_collection(COLLECTION)

    current_movie = collection.find_one({"tconst": tconst})
    if not current_movie:
        return {"data": f"Movie {tconst} not found"}, 404

    fields = {
        "magnet_link": magnet_link,
        "references": references,
        "soundtrack": soundtrack,
        "watched": watched,
        "wiki": wiki,
    }
    update_data = {field: value for field, value in fields.items() if value is not None}

    # Rewrites the existing references when none were sent. It is a no-op on the
    # document, but it keeps update_data non-empty so a PUT carrying no field
    # still answers 200 instead of 400.
    if references is None and "references" in current_movie:
        update_data["references"] = current_movie["references"]

    if not update_data:
        return {"data": "No fields to update"}, 400

    sync_blogpost(tconst, update_data)

    try:
        updated_movie = collection.find_one_and_update(
            {"tconst": tconst},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )
        updated_movie["_id"] = str(updated_movie["_id"])
        return {"data": updated_movie}, 200
    except Exception as e:
        logger.error("Could not update %s: %s", tconst, e)
        return {"data": "Failed to update favorited movie"}, 500


# Remove um filme dos favoritos
def delete_favorited_movie(tconst):
    collection = get_mongo_collection(COLLECTION)

    try:
        if collection.delete_one({"tconst": tconst}).deleted_count == 0:
            return {"data": f"Movie {tconst} not found"}, 404
        return {"data": f"Movie {tconst} deleted"}, 200
    except Exception as e:
        logger.error("Could not delete %s: %s", tconst, e)
        return {"data": "Failed to delete listed movie"}, 500


# Campos que a listagem do frontend realmente usa. O documento completo carrega
# trivia, quote, plot e plot_keywords, que só fazem sentido na tela de detalhe -
# essa busca o filme inteiro pelo GET /favorites/<tconst>.
LIST_PROJECTION = {
    "poster_url": 1,
    "primaryTitle": 1,
    "tconst": 1,
    "watched": 1,
}


# Recupera os filmes favoritados
def get_favorited_movies(
    filters=None, sorters=("_id", -1), page=1, page_size=0, search_term=""
):
    collection = get_mongo_collection(COLLECTION)

    # Copied so the caller's dict (the request body) is never mutated.
    filters = dict(filters or {})
    search_term = search_term or filters.get("search_term") or filters.get("tconst")

    # Filtra `search_term` no campo `tconst` ou `primaryTitle`
    if search_term:
        # Garante que search_term seja uma string para usar com $regex
        search_term_str = str(search_term) if search_term else ""
        if search_term_str:
            filters["$or"] = [
                {"tconst": search_term},
                {"primaryTitle": {"$regex": search_term_str, "$options": "i"}},
                {"director": {"$regex": search_term_str, "$options": "i"}},
            ]

    country = filters.get("country")
    if country:
        filters["country"] = country

    # Sanitiza os filtros para garantir que valores $regex sejam strings
    filters = sanitize_filters(filters)

    try:
        unique_countries = collection.distinct("country")
        unique_years = [
            int(year) for year in collection.distinct("startYear")
            if year is not None and str(year).isdigit()
        ]

        total_documents = collection.count_documents(filters)
        skip = (page - 1) * page_size if page_size else 0
        query = collection.find(filters, LIST_PROJECTION).sort(sorters[0], sorters[1]).skip(skip)
        if page_size:
            query = query.limit(page_size)
        items = list(query)

        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        return {
            "total_documents": total_documents,
            "entries": items,
            "countries": unique_countries,
            "years": unique_years,
        }, 200
    except Exception as e:
        logger.error("Could not search favorites: %s", e)
        return {"status": 500, "message": "Internal server error"}, 500
