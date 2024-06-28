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

def read_tsv_in_chunks(file_path, chunk_size):
    logging.info(f'Iniciando a leitura do arquivo TSV em chunks: {file_path}')

    for chunk in pd.read_csv(file_path, sep='\t', chunksize=chunk_size, low_memory=False):
        yield chunk

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

def process_in_chunks(file_path, db_name, collection_name, num_chunks):
    # Calculando o tamanho do chunk com base no número de chunks desejado
    total_lines = sum(1 for line in open(file_path)) - 1  # -1 para descontar o cabeçalho
    chunk_size = total_lines // num_chunks
    
    chunk_num = 0
    for chunk in read_tsv_in_chunks(file_path, chunk_size):
        chunk_num += 1
        logging.info(f'Processando chunk {chunk_num} de {num_chunks}')
        insert_into_mongo(db_name, collection_name, chunk)

process_in_chunks(file_path, db_name, collection_name, 10)