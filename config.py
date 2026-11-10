import logging
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_CONNECTION_STRING_ATLAS = os.getenv("MONGODB_CONNECTION_STRING_ATLAS")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")


class DatabaseUnavailable(Exception):
    """Raised when MongoDB cannot be reached. app.py turns it into a 503."""


# Reused across requests: MongoClient keeps its own connection pool.
_mongo_client = None


def get_mongo_client():
    global _mongo_client
    if _mongo_client:
        return _mongo_client

    try:
        client = MongoClient(
            MONGODB_CONNECTION_STRING_ATLAS, serverSelectionTimeoutMS=5000
        )
        client.server_info()  # Testa conexão
    except PyMongoError as e:
        logger.error("Could not connect to MongoDB Atlas: %s", e)
        raise DatabaseUnavailable("MongoDB Atlas indisponível") from e

    logger.info("MongoDB Atlas connection established")
    _mongo_client = client
    return client


def get_mongo_collection(name):
    """Retorna uma coleção MongoDB, reutilizando a conexão.

    Raises DatabaseUnavailable when the server cannot be reached, so callers
    never have to check for None.
    """
    return get_mongo_client()[MONGODB_DATABASE][name]


# Mongo collections
FAVORITES_COLLECTION = "favoritelist"
REVIEWS_COLLECTION = "authoralreviewslist"
SERIES_COLLECTION = "serieslist"
KEYWORDS_COLLECTION = "favorites_keywords"
MAIN_IMAGES_COLLECTION = "main-images"
BLOGPOSTS_COLLECTION = "blogposts"

# Configurações da RapidAPI
RAPIDAPI_API_KEY = os.getenv("RAPIDAPI_API_KEY")

# AWS / S3. Only the images feature needs these; it validates them on use so
# the rest of the API still boots without them.
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv("S3_BUCKET", "themoviesearch")

# Timeout for every outbound HTTP call that is not the IMDB scraper.
HTTP_TIMEOUT = 15

# Configurações da OpenSubtitles
OPEN_SUBTITLES_API_KEY = os.getenv("OPEN_SUBTITLES_API_KEY")
