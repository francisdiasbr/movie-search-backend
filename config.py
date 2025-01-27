import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

MONGODB_CONNECTION_STRING_ATLAS = os.getenv("MONGODB_CONNECTION_STRING_ATLAS")
MONGODB_CONNECTION_STRING_LOCAL = os.getenv("MONGODB_CONNECTION_STRING_LOCAL")

# Conexão com o MongoDB
atlas_client = MongoClient(MONGODB_CONNECTION_STRING_ATLAS)
local_client = MongoClient(MONGODB_CONNECTION_STRING_LOCAL)

atlas_db = atlas_client[os.getenv("MONGODB_DATABASE")]
local_db = local_client[os.getenv("MONGODB_DATABASE")]

# Função para obter uma coleção do MongoDB
def get_mongo_collection(name, use_atlas=True):
    if use_atlas:
        collection = atlas_db[name]
        return collection
    else:
        collection = local_db[name]
        return collection

# Configurações da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configurações da Serper API
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Configurações da RapidAPI
RAPIDAPI_API_KEY = os.getenv("RAPIDAPI_API_KEY")

# Configurações do Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Verifica se as credenciais AWS estão carregadas
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    raise Exception("Credenciais AWS não foram carregadas corretamente.")

# Configurações da OpenSubtitles
OPEN_SUBTITLES_API_KEY = os.getenv("OPEN_SUBTITLES_API_KEY")
