from pymongo import MongoClient

from dotenv import load_dotenv

import os

load_dotenv()


def get_mongo_client():

    client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))

    return client


def get_mongo_db():

    client = get_mongo_client()

    db = client["movie-search"]

    return db


def get_mongo_collection(name):

    db = get_mongo_db()

    collection = db[name]

    return collection


def logger(color, title, description, message):

    if color == "red":
        id = 31
    elif color == "green":
        id = 32
    elif color == "yellow":
        id = 33
    elif color == "blue":
        id = 34
    elif color == "purple":
        id = 35
    elif color == "gray":
        id = 30

    print(f"\n\033[{id};1m{title}\033[0m \033[30;1m[ {description} ]\033[0m {message}")