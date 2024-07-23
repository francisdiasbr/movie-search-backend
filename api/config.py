import os

from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do Flask
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

# Conexão com o MongoDB
client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))
db = client[os.getenv("MONGODB_DATABASE")]

# Função para obter uma coleção do MongoDB
def get_mongo_collection(name):

    collection = db[name]
    return collection