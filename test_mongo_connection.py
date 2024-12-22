from pymongo import MongoClient
from config import MONGODB_CONNECTION_STRING_ATLAS, MONGODB_CONNECTION_STRING_LOCAL

def test_connection(connection_string, db_name, connection_type):
    try:
        # Cria uma instância do cliente MongoDB
        client = MongoClient(connection_string)
        
        # Tenta acessar o banco de dados
        db = client[db_name]
        # Executa um comando simples para verificar a conexão
        db.command("ping")
        
        print(f"Conexão com o MongoDB {connection_type} foi bem-sucedida!")
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB {connection_type}: {e}")

if __name__ == "__main__":
    # Testa a conexão com o MongoDB Atlas
    test_connection(MONGODB_CONNECTION_STRING_ATLAS, "movie-search", "Atlas")
    
    # Testa a conexão com o MongoDB Local
    test_connection(MONGODB_CONNECTION_STRING_LOCAL, "movie-search", "Local")
