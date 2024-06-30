import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

file_path = os.getenv('TITLE_BASICS_FILE_PATH')
db_name = os.getenv('DB_NAME')
collection_name = os.getenv('COLLECTION_NAME_TITLE_BASICS')

def read_tsv(file_path):
    df = pd.read_csv(file_path, sep='\t', low_memory=False)
    return df

def insert_into_mongo(db_name, collection_name, dataframe):
    dataframe['startYear'] = pd.to_numeric(dataframe['startYear'], errors='coerce')
    dataframe['endYear'] = pd.to_numeric(dataframe['endYear'], errors='coerce')
    dataframe['genres'] = dataframe['genres'].apply(lambda x: x.split(',') if pd.notna(x) else [])
    
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    collection = db[collection_name]

    data_dict = dataframe.to_dict(orient='records')
    collection.insert_many(data_dict)

    print(f'{len(data_dict)} registros inseridos na coleção "{collection_name}" do banco de dados "{db_name}".')

dataframe = read_tsv(file_path)

insert_into_mongo(db_name, collection_name, dataframe)
