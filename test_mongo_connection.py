from pymongo import MongoClient

from config import MONGODB_CONNECTION_STRING

def test_connection():
    try:
        # Cria uma instância do cliente MongoDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        
        # Tenta acessar o banco de dados
        db = client.movie_search  # Substitua 'test' pelo nome do seu banco de dados, se necessário
        # Executa um comando simples para verificar a conexão
        db.command("ping")
        
        print("Conexão com o MongoDB Atlas foi bem-sucedida!")
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB Atlas: {e}")

if __name__ == "__main__":
    test_connection()
