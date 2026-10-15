"""Mongo helpers shared by every feature.

Controllers get a collection with `get_mongo_collection` and go through these
helpers so that `_id` serialization, NaN cleanup, pagination and partial
updates are written once.
"""

from pymongo import ReturnDocument

from utils import sanitize_filters, sanitize_movie_data


def serialize(doc):
    """Makes a Mongo document JSON-ready: `_id` as str, NaN/inf as None."""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return sanitize_movie_data(doc)


def insert(collection, doc):
    doc["_id"] = collection.insert_one(doc).inserted_id
    return serialize(doc)


def search(collection, filters=None, projection=None, sort=("_id", -1), page=1, page_size=0):
    """Counts and lists documents matching `filters`.

    page_size=0 means no pagination. Returns (total_documents, entries).
    """
    filters = sanitize_filters(filters or {})
    total = collection.count_documents(filters)
    cursor = collection.find(filters, projection).sort(*sort)
    if page_size:
        cursor = cursor.skip((page - 1) * page_size).limit(page_size)
    return total, [serialize(doc) for doc in cursor]


def update(collection, query, fields):
    """Sets the non-None `fields` on the matching document.

    Sending no field is a valid, idempotent request: the current document is
    returned. Returns None when nothing matches `query`.
    """
    fields = {key: value for key, value in fields.items() if value is not None}
    if fields:
        doc = collection.find_one_and_update(
            query, {"$set": fields}, return_document=ReturnDocument.AFTER
        )
    else:
        doc = collection.find_one(query)
    return serialize(doc)


def delete(collection, query):
    """Returns True when a document was removed."""
    return collection.delete_one(query).deleted_count > 0
