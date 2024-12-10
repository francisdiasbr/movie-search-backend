import os

from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configurações da Serper API
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Configurações da RapidAPI
RAPIDAPI_API_KEY = os.getenv("RAPIDAPI_API_KEY")

# Configurações do Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Configurações do Flask
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# Conexão com o MongoDB
client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))
db = client[os.getenv("MONGODB_DATABASE")]


# Função para obter uma coleção do MongoDB
def get_mongo_collection(name):
    collection = db[name]
    return collection
