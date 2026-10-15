import logging
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_CONNECTION_STRING_ATLAS = os.getenv("MONGODB_CONNECTION_STRING_ATLAS")
MONGODB_CONNECTION_STRING_LOCAL = os.getenv("MONGODB_CONNECTION_STRING_LOCAL")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")


class DatabaseUnavailable(Exception):
    """Raised when MongoDB cannot be reached. app.py turns it into a 503."""


# Clientes MongoDB reutilizáveis (singleton)
_mongo_client_atlas = None
_mongo_client_local = None


def get_mongo_client(use_atlas=True):
    """Retorna cliente MongoDB reutilizável (singleton)"""
    global _mongo_client_atlas, _mongo_client_local
    connection_type = "Atlas" if use_atlas else "Local"

    if use_atlas and _mongo_client_atlas:
        return _mongo_client_atlas
    if not use_atlas and _mongo_client_local:
        return _mongo_client_local

    connection_string = (
        MONGODB_CONNECTION_STRING_ATLAS if use_atlas else MONGODB_CONNECTION_STRING_LOCAL
    )
    try:
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.server_info()  # Testa conexão
    except PyMongoError as e:
        logger.error("Could not connect to MongoDB %s: %s", connection_type, e)
        raise DatabaseUnavailable(f"MongoDB {connection_type} indisponível") from e

    logger.info("MongoDB %s connection established", connection_type)
    if use_atlas:
        _mongo_client_atlas = client
    else:
        _mongo_client_local = client
    return client


def get_mongo_collection(name, use_atlas=True):
    """Retorna uma coleção MongoDB, reutilizando conexões.

    Raises DatabaseUnavailable when the server cannot be reached, so callers
    never have to check for None.
    """
    return get_mongo_client(use_atlas)[MONGODB_DATABASE][name]


# Configurações da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
