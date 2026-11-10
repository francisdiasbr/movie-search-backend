"""Shared fixtures.

No test may reach Atlas, S3 or IMDB: Mongo is replaced by mongomock for every
test (autouse), and each test module mocks the external calls of the
controller it covers.
"""

import mongomock
import pytest

import config


@pytest.fixture(autouse=True)
def mongo(monkeypatch):
    """In-memory database that `config.get_mongo_collection` hands out."""
    client = mongomock.MongoClient()
    monkeypatch.setattr(config, "get_mongo_client", lambda: client)
    monkeypatch.setattr(config, "MONGODB_DATABASE", "test")
    return client["test"]


@pytest.fixture
def favorites(mongo):
    return mongo[config.FAVORITES_COLLECTION]
