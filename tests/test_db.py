import pytest
from bson import ObjectId

import db


@pytest.fixture
def movies(mongo):
    collection = mongo["movies"]
    collection.insert_many(
        [
            {"tconst": f"tt{n}", "primaryTitle": title, "startYear": year}
            for n, (title, year) in enumerate(
                [
                    ("The 400 Blows", 1959),
                    ("Breathless", 1960),
                    ("Jules and Jim", 1962),
                    ("Pierrot le Fou", 1965),
                    ("Day for Night", 1973),
                ],
                start=1,
            )
        ]
    )
    return collection


def test_serialize_none_stays_none():
    assert db.serialize(None) is None


def test_serialize_makes_the_document_json_ready():
    _id = ObjectId()
    doc = db.serialize({"_id": _id, "rating": float("nan"), "tconst": "tt1"})

    assert doc == {"_id": str(_id), "rating": None, "tconst": "tt1"}


def test_insert_stores_and_returns_the_serialized_document(mongo):
    doc = db.insert(mongo["movies"], {"tconst": "tt1", "rating": float("nan")})

    assert isinstance(doc["_id"], str)
    assert doc["rating"] is None
    assert mongo["movies"].find_one({"_id": ObjectId(doc["_id"])})["tconst"] == "tt1"


def test_search_without_filters_lists_everything_newest_first(movies):
    total, entries = db.search(movies)

    assert total == 5
    assert [e["tconst"] for e in entries] == ["tt5", "tt4", "tt3", "tt2", "tt1"]
    assert all(isinstance(e["_id"], str) for e in entries)


def test_search_filters_and_counts(movies):
    total, entries = db.search(movies, {"startYear": {"$gte": 1962}})

    assert total == 3
    assert {e["tconst"] for e in entries} == {"tt3", "tt4", "tt5"}


def test_search_paginates_but_counts_every_match(movies):
    total, entries = db.search(movies, sort=("startYear", 1), page=2, page_size=2)

    assert total == 5
    assert [e["tconst"] for e in entries] == ["tt3", "tt4"]


def test_search_last_page_may_be_short(movies):
    _, entries = db.search(movies, sort=("startYear", 1), page=3, page_size=2)
    assert [e["tconst"] for e in entries] == ["tt5"]


def test_search_applies_the_projection(movies):
    _, entries = db.search(movies, {"tconst": "tt1"}, projection={"primaryTitle": 1})
    assert set(entries[0]) == {"_id", "primaryTitle"}


def test_search_sanitizes_the_filters(movies):
    # A numeric $regex would make Mongo fail; sanitize_filters turns it into "400".
    total, entries = db.search(movies, {"primaryTitle": {"$regex": 400}})

    assert total == 1
    assert entries[0]["tconst"] == "tt1"


def test_update_sets_only_the_non_none_fields(movies):
    doc = db.update(movies, {"tconst": "tt1"}, {"watched": True, "startYear": None})

    assert doc["watched"] is True
    assert doc["startYear"] == 1959
    assert movies.find_one({"tconst": "tt1"})["watched"] is True


def test_update_keeps_falsy_values_that_are_not_none(movies):
    doc = db.update(movies, {"tconst": "tt1"}, {"watched": False, "wiki": ""})

    assert doc["watched"] is False
    assert doc["wiki"] == ""


def test_update_without_fields_returns_the_current_document(movies):
    doc = db.update(movies, {"tconst": "tt2"}, {})
    assert doc["primaryTitle"] == "Breathless"


def test_update_returns_none_when_nothing_matches(movies):
    assert db.update(movies, {"tconst": "tt99"}, {"watched": True}) is None
    assert db.update(movies, {"tconst": "tt99"}, {}) is None


def test_delete_tells_whether_a_document_was_removed(movies):
    assert db.delete(movies, {"tconst": "tt1"}) is True
    assert db.delete(movies, {"tconst": "tt1"}) is False
    assert movies.count_documents({}) == 4
