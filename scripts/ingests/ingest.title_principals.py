import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import logging

load_dotenv()

file_path = os.getenv('TITLE_PRINCIPALS_FILE_PATH')
db_name = os.getenv('DB_NAME')
collection_name = os.getenv('COLLECTION_NAME_TITLE_PRINCIPALS')

# Configurando o logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_tsv(file_path):
    logging.info(f'Iniciando a leitura do arquivo TSV: {file_path}')
    df = pd.read_csv(file_path, sep='\t', low_memory=False)
    return df

def insert_into_mongo(db_name, collection_name, dataframe):
    logging.info(f'Iniciando a inserção de dados no MongoDB - Banco de dados: {db_name}, Coleção: {collection_name}')
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client[db_name]
        collection = db[collection_name]

        data_dict = dataframe.to_dict(orient='records')
        collection.insert_many(data_dict)

        print(f'{len(data_dict)} registros inseridos na coleção "{collection_name}" do banco de dados "{db_name}".')
    
    except Exception as e:
        logging.error(f'Erro ao inserir dados no MongoDB: {e}')
        raise

def insert_in_chunks(dataframe, db_name, collection_name, chunk_size=4):
    total_rows = len(dataframe)
    chunk_size = total_rows // chunk_size
    for i in range(0, total_rows, chunk_size):
        chunk = dataframe.iloc[i:i + chunk_size]
        insert_into_mongo(db_name, collection_name, chunk)
        logging.info(f'Chunk {i//chunk_size + 1} inserido com sucesso.')

dataframe = read_tsv(file_path)

insert_in_chunks(dataframe, db_name, collection_name)