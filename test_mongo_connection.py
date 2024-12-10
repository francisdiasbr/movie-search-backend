from pymongo import MongoClient
import os

# Substitua pela sua string de conexão do MongoDB Atlas
MONGODB_CONNECTION_STRING = "mongodb+srv://francisdiasbr:Amor2020!@cluster0.a6327.mongodb.net/"

def test_connection():
    try:
        # Cria uma instância do cliente MongoDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        
        # Tenta acessar o banco de dados
        db = client.test  # Substitua 'test' pelo nome do seu banco de dados, se necessário
        # Executa um comando simples para verificar a conexão
        db.command("ping")
        
        print("Conexão com o MongoDB Atlas foi bem-sucedida!")
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB Atlas: {e}")

if __name__ == "__main__":
    test_connection()
