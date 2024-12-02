from bson import ObjectId
from config import get_mongo_collection

def ratings_retrieve(tconst):
    collection = get_mongo_collection("titleratings")

    try:
        if not tconst:
            return {"data": "Id is required"}

        item = collection.find_one({"tconst": tconst})

        if item:
            item["_id"] = str(item["_id"])

    except Exception as e:
        print(f"{e}")
        return {"status": 400, "data": "Exception when retrieving item"}

    return {"data": item}

def ratings_search(filters={}, sorters=["tconst", -1], page=1, page_size=10):
    collection = get_mongo_collection("titleratings")

    if filters.get("_id"):
        filters["_id"] = ObjectId(filters["_id"])

    if 'numVotes' in filters:
        if isinstance(filters['numVotes'], dict):
            if "$gt" in filters['numVotes']:
                try:
                    filters['numVotes']['$gt'] = int(filters['numVotes']['$gt'])
                except ValueError:
                    return {"payload": [], "total_documents": 0, "error": "numVotes must be an integer"}
            if "$lt" in filters['numVotes']:
                try:
                    filters['numVotes']['$lt'] = int(filters['numVotes']['$lt'])
                except ValueError:
                    return {"payload": [], "total_documents": 0, "error": "numVotes must be an integer"}
        else:
            try:
                filters['numVotes'] = int(filters['numVotes'])
            except ValueError:
                return {"payload": [], "total_documents": 0, "error": "numVotes must be an integer"}

    if 'averageRating' in filters:
        if isinstance(filters['averageRating'], dict):
            if "$gt" in filters['averageRating']:
                try:
                    filters['averageRating']['$gt'] = float(filters['averageRating']['$gt'])
                except ValueError:
                    return {"payload": [], "total_documents": 0, "error": "averageRating must be a float"}
            if "$lt" in filters['averageRating']:
                try:
                    filters['averageRating']['$lt'] = float(filters['averageRating']['$lt'])
                except ValueError:
                    return {"payload": [], "total_documents": 0, "error": "averageRating must be a float"}
        else:
            try:
                filters['averageRating'] = float(filters['averageRating'])
            except ValueError:
                return {"payload": [], "total_documents": 0, "error": "averageRating must be a float"}

    total_documents = 0

    try:
        documents = []

        print(f"filters: {filters}")

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
        print(f"{e}")
        documents = []

    return {"total_documents": total_documents, "payload": documents}

def movie_with_rating_retrieve(tconst):
    basics_collection = get_mongo_collection("titlebasics")

    try:
        if not tconst:
            return {"data": "Id is required"}

        movie_details = basics_collection.find_one({"tconst": tconst})
        if movie_details:
            result = {
                "tconst": movie_details.get("tconst"),
                "originalTitle": movie_details.get("originalTitle"),
                "primaryTitle": movie_details.get("primaryTitle"),
                "startYear": movie_details.get("startYear"),
            }
            return {"data": result}
        else:
            return {"status": 404, "data": "Movie details not found"}

    except Exception as e:
        print(f"{e}")
        return {"status": 400, "data": "Exception when retrieving item"}