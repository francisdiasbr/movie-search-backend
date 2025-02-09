import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

MONGODB_CONNECTION_STRING_ATLAS = os.getenv("MONGODB_CONNECTION_STRING_ATLAS")
MONGODB_CONNECTION_STRING_LOCAL = os.getenv("MONGODB_CONNECTION_STRING_LOCAL")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")

def get_mongo_client(use_atlas=True):
    try:
        if use_atlas:
            client = MongoClient(MONGODB_CONNECTION_STRING_ATLAS)
            connection_type = "Atlas"
        else:
            client = MongoClient(MONGODB_CONNECTION_STRING_LOCAL)
            connection_type = "Local"
        
        # Testa a conexão
        client.server_info()
        print(f"Conexão com MongoDB {connection_type} estabelecida com sucesso")
        return client
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB {connection_type}: {e}")
        print(f"String de conexão usada: {'Atlas' if use_atlas else MONGODB_CONNECTION_STRING_LOCAL}")
        return None

# Função para obter uma coleção do MongoDB
def get_mongo_collection(name, use_atlas=True):
    try:
        client = get_mongo_client(use_atlas)
        if client:
            db = client[MONGODB_DATABASE]
            return db[name]
        else:
            print(f"Não foi possível obter cliente MongoDB {'Atlas' if use_atlas else 'Local'}")
            return None
    except Exception as e:
        print(f"Erro ao obter coleção {name}: {e}")
        return None

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
