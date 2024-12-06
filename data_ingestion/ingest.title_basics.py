import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

file_path = os.getenv("TITLE_BASICS_FILE_PATH")
collection_name = os.getenv("COLLECTION_NAME_TITLE_BASICS")


def read_tsv(file_path):
    print(f"Iniciando a leitura do arquivo TSV: {file_path}")
    try:
        df = pd.read_csv(file_path, sep="\t", low_memory=False)
        df = df[df["titleType"] == "movie"]
        print(f"Leitura do arquivo TSV concluída: {file_path}")
        return df
    except Exception as e:
        print(f"Erro ao ler o arquivo TSV: {e}")
        raise


def insert_into_mongo(collection_name, dataframe):
    print(f"Iniciando a inserção de dados no MongoDB - Coleção: {collection_name}")
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["movie-search"]
        collection = db[collection_name]

        dataframe["startYear"] = pd.to_numeric(dataframe["startYear"], errors="coerce")

        dataframe.drop(
            columns=["genres", "endYear", "runtimeMinutes", "isAdult"], inplace=True
        )

        data_dict = dataframe.to_dict(orient="records")
        collection.insert_many(data_dict)
        print(f'{len(data_dict)} registros inseridos na coleção "{collection_name}".')
    except Exception as e:
        print(f"Erro ao inserir dados no MongoDB: {e}")
        raise
    finally:
        client.close()
        print("Conexão com MongoDB fechada.")


def main():
    try:
        dataframe = read_tsv(file_path)
        insert_into_mongo(collection_name, dataframe)
    except Exception as e:
        print(f"Erro durante o processo: {e}")


if __name__ == "__main__":
    main()
