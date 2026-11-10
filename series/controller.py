import logging
from datetime import datetime

import db
from config import SERIES_COLLECTION, get_mongo_collection
from keywords.imdb import IMDBSearchError, find_brazilian_title, find_series
from utils import error, pick

logger = logging.getLogger(__name__)


def series():
    return get_mongo_collection(SERIES_COLLECTION)


# Fields the client may change on a series.
EDITABLE_FIELDS = ("watched",)

# What the list shows; plot, creators and stars stay in the full document.
LIST_PROJECTION = {
    "endYear": 1,
    "episodes": 1,
    "genres": 1,
    "imdb_rating": 1,
    "poster_url": 1,
    "primaryTitle": 1,
    "seasons": 1,
    "startYear": 1,
    "tconst": 1,
    "title_pt": 1,
    "watched": 1,
}


def add_series(tconst):
    """Saves the series `tconst` with what IMDB's API says about it.

    Everything comes from IMDB's GraphQL API, so no session or scraper is
    involved and the answer takes a second.
    """
    collection = series()
    if collection.find_one({"tconst": tconst}):
        return error("Série já está na lista", 409)

    try:
        found = find_series(tconst)
        title_pt = find_brazilian_title(tconst) if found else None
    except IMDBSearchError as e:
        logger.error("%s", e)
        return error("IMDb não respondeu à consulta da série", 502)

    if not found:
        return error("Título não encontrado no IMDb", 404)
    if not found.pop("is_series"):
        return error("Esse título não é uma série", 400)

    doc = db.insert(
        collection,
        {
            **found,
            "title_pt": title_pt or "",
            "imdb_url": f"https://www.imdb.com/title/{tconst}/",
            "watched": False,
            "created_at": datetime.now().isoformat(),
        },
    )
    logger.info("Series %s added as %s", tconst, doc["_id"])
    return {"data": doc}, 201


def get_series(tconst):
    doc = db.serialize(series().find_one({"tconst": tconst}))
    if not doc:
        return error("Série não encontrada", 404)
    return {"data": doc}, 200


def list_series(filters=None, page=1, page_size=0, search_term=""):
    filters = dict(filters or {})
    if search_term:
        term = str(search_term)
        filters["$or"] = [
            {"tconst": term},
            {"primaryTitle": {"$regex": term, "$options": "i"}},
            {"title_pt": {"$regex": term, "$options": "i"}},
        ]

    total, entries = db.search(
        series(),
        filters,
        projection=LIST_PROJECTION,
        sort=("primaryTitle", 1),
        page=page,
        page_size=page_size,
    )
    return {"total_documents": total, "entries": entries}, 200


def edit_series(tconst, request_data):
    """Updates only the fields present in the body; the others are kept."""
    doc = db.update(series(), {"tconst": tconst}, pick(request_data, EDITABLE_FIELDS))
    if not doc:
        return error("Série não encontrada", 404)
    return {"data": doc}, 200


def delete_series(tconst):
    if not db.delete(series(), {"tconst": tconst}):
        return error("Série não encontrada", 404)
    return {"data": f"Series {tconst} deleted"}, 200
