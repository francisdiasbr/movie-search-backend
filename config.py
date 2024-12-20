import os

from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()


# String de conexão com o MongoDB
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")

# Configurações da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configurações da Serper API
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Configurações da RapidAPI
RAPIDAPI_API_KEY = os.getenv("RAPIDAPI_API_KEY")

# Configurações do Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


# Conexão com o MongoDB
client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))
db = client[os.getenv("MONGODB_DATABASE")]


# Função para obter uma coleção do MongoDB
def get_mongo_collection(name):
    collection = db[name]
    return collection

# Verifica se as credenciais AWS estão carregadas
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    raise Exception("Credenciais AWS não foram carregadas corretamente.")

