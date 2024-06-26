import pandas as pd
from pymongo import MongoClient
import logging
import os
from dotenv import load_dotenv

load_dotenv()

file_path = os.getenv('TITLE_RATINGS_FILE_PATH')
db_name = os.getenv('DB_NAME')
collection_name = os.getenv('COLLECTION_NAME_TITLE_RATINGS')

# Configurando o logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para ler o arquivo TSV e converter para um DataFrame do pandas
def read_tsv(file_path):
    logging.info(f'Iniciando a leitura do arquivo TSV: {file_path}')
    df = pd.read_csv(file_path, sep='\t', low_memory=False)
    return df

# Função para inserir o DataFrame no MongoDB
def insert_into_mongo(db_name, collection_name, dataframe):
    logging.info(f'Iniciando a inserção de dados no MongoDB - Banco de dados: {db_name}, Coleção: {collection_name}')
    try:
      client = MongoClient('mongodb://localhost:27017/')
      db = client[db_name]
      collection = db[collection_name]

      # convertendo o dataframe para um dicionario e inserindo no MongoDB
      data_dict = dataframe.to_dict(orient='records')
      collection.insert_many(data_dict)

      print(f'{len(data_dict)} registros inseridos na coleção "{collection_name}" do banco de dados "{db_name}".')
    
    except Exception as e:
      logging.error(f'Erro ao inserir dados no MongoDB: {e}')
      raise

# Lendo o arquivo TSV e inserindo no MongoDB
dataframe = read_tsv(file_path)

# Inserindo no MongoDB
insert_into_mongo(db_name, collection_name, dataframe)
