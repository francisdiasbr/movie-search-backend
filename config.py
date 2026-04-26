import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

MONGODB_CONNECTION_STRING_ATLAS = os.getenv("MONGODB_CONNECTION_STRING_ATLAS")
MONGODB_CONNECTION_STRING_LOCAL = os.getenv("MONGODB_CONNECTION_STRING_LOCAL")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")


# Clientes MongoDB reutilizáveis (singleton)
_mongo_client_atlas = None
_mongo_client_local = None

def get_mongo_client(use_atlas=True):
    """Retorna cliente MongoDB reutilizável (singleton)"""
    global _mongo_client_atlas, _mongo_client_local
    connection_type = "Atlas" if use_atlas else "Local"
    
    # Retorna cliente existente se já estiver criado
    if use_atlas and _mongo_client_atlas:
        return _mongo_client_atlas
    if not use_atlas and _mongo_client_local:
        return _mongo_client_local
    
    # Cria novo cliente apenas se não existir
    try:
        if use_atlas:
            client = MongoClient(MONGODB_CONNECTION_STRING_ATLAS)
            client.server_info()  # Testa conexão
            _mongo_client_atlas = client
            print(f"Conexão com MongoDB {connection_type} estabelecida com sucesso (reutilizável)")
            return _mongo_client_atlas
        else:
            client = MongoClient(MONGODB_CONNECTION_STRING_LOCAL)
            client.server_info()  # Testa conexão
            _mongo_client_local = client
            print(f"Conexão com MongoDB {connection_type} estabelecida com sucesso (reutilizável)")
            return _mongo_client_local
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB {connection_type}: {e}")
        return None


# Função para obter uma coleção do MongoDB
def get_mongo_collection(name, use_atlas=True):
    """Retorna uma coleção MongoDB, reutilizando conexões"""
    try:
        client = get_mongo_client(use_atlas)
        if client:
            db = client[MONGODB_DATABASE]
            return db[name]
        else:
            print(
                f"Não foi possível obter cliente MongoDB {'Atlas' if use_atlas else 'Local'}"
            )
            return None
    except Exception as e:
        print(f"Erro ao obter coleção {name}: {e}")
        return None


# Configurações da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configurações da Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Configurações do Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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