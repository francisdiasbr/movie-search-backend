from bson import ObjectId

from config import logger, get_mongo_collection


def crew_retrieve(item_id):

    collection = get_mongo_collection("titlecrew")

    try:
        if not item_id:
            return {"status": 400, "data": "Id is required"}

        item = collection.find_one({"_id": ObjectId(item_id)})

        if item:
            item["_id"] = str(item["_id"])

    except Exception as e:

        logger("red", "crew", "crew_retrieve", f"{e}")

        return {"status": 400, "data": "Exception when retrieving item"}

    return {"status": 200, "data": item}

def crew_search(filters={}, sorters=["_id", -1], page=1, page_size=10):

    collection = get_mongo_collection("titlecrew")

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