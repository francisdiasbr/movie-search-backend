from bson import ObjectId

from config import logger, get_mongo_collection


def movies_create(movie_data):

    collection = get_mongo_collection("movies")

    try:
        if not movie_data:
            return {"status": 400, "data": "Data is required"}

        titleName = movie_data.get("primaryTitle")

        existing_title = collection.find_one(
            {"name": titleName}
        )
        if existing_title:
            return {"status": 400, "data": "Title with the same name already exists"}

        saved = collection.insert_one(movie_data)

        saved_id = str(saved.inserted_id)

    except Exception as e:

        logger("red", "movies", "movies_create", f"{e}")

        return {"status": 400, "data": "Exception when saving item"}

    return {"status": 200, "data": saved_id}


def movies_delete(item_id):

    collection = get_mongo_collection("movies")

    try:
        if not item_id:
            return {"status": 400, "data": "Id is required"}

        item = collection.find_one({"_id": ObjectId(item_id)})

        if not item:
            return {"status": 404, "data": "Item not found"}

        collection.delete_one({"_id": ObjectId(item_id)})

    except Exception as e:

        logger("red", "movies", "movies_delete", f"{e}")

        return {"status": 400, "data": "Exception when deleting item"}

    return {"status": 200, "data": "movie deleted"}


def movies_retrieve(item_id):

    collection = get_mongo_collection("movies")

    try:
        if not item_id:
            return {"status": 400, "data": "Id is required"}

        item = collection.find_one({"_id": ObjectId(item_id)})

        if item:
            item["_id"] = str(item["_id"])

    except Exception as e:

        logger("red", "movie", "movies_retrieve", f"{e}")

        return {"status": 400, "data": "Exception when retrieving item"}

    return {"status": 200, "data": item}


def movies_search(filters={}, sorters=["_id", -1], page=1, page_size=10):

    collection = get_mongo_collection("movies")

    if filters.get("_id"):
        filters["_id"] = ObjectId(filters["_id"])

    total_documents = 0

    try:
        documents = []

        total_documents = collection.count_documents(filters)

        skip = (page - 1) * page_size

        for item in (
            collection.find(filters)
            .sort(sorters[0], sorters[1])
            .skip(skip)
            .limit(page_size)
        ):

            item["_id"] = str(item["_id"])

            documents.append(item)

    except Exception as e:

        documents = []

    return {"payload": documents, "total_documents": total_documents}


def movies_update(item_id, movie_data):

    collection = get_mongo_collection("movies")

    try:
        if not item_id:
            return {"status": 400, "data": "Id is required"}

        if not movie_data:
            return {"status": 400, "data": "Data is required"}

        collection.update_one({"_id": ObjectId(item_id)}, {"$set": movie_data})

    except Exception as e:

        logger("red", "movies", "movies_update", f"{e}")

        return {"status": 400, "data": "Exception when updating item"}

    return {"status": 200, "data": "movie updated"}
