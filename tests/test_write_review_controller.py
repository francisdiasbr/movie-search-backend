import pytest

import config
from write_review import controller

REVIEW = {"content": {"pt": {"text": "Uma obra-prima."}}}


@pytest.fixture
def reviews(mongo):
    return mongo[config.REVIEWS_COLLECTION]


@pytest.fixture
def favorite(favorites):
    favorites.insert_one({"tconst": "tt1", "primaryTitle": "Breathless"})


def test_create_review_saves_it_with_the_defaults(favorite, reviews):
    body, status = controller.create_and_save_movie_review("tt1", REVIEW)

    assert status == 201
    assert body["data"]["content"] == REVIEW["content"]
    assert body["data"]["primaryTitle"] == "Breathless"
    assert body["data"]["isAiGenerated"] is False
    assert body["data"]["references"] == []
    assert body["data"]["images"] == []
    assert reviews.count_documents({"tconst": "tt1"}) == 1


def test_create_review_requires_the_movie_to_be_a_favorite(reviews):
    _, status = controller.create_and_save_movie_review("tt1", REVIEW)

    assert status == 404
    assert reviews.count_documents({}) == 0


def test_create_review_refuses_a_second_review(favorite, reviews):
    controller.create_and_save_movie_review("tt1", REVIEW)

    assert controller.create_and_save_movie_review("tt1", REVIEW)[1] == 409
    assert reviews.count_documents({}) == 1


@pytest.mark.parametrize(
    "review_data",
    [
        None,
        {},
        {"content": {}},
        {"content": {"pt": {"text": ""}}},
        {"content": {"en": {"text": "x"}}},
    ],
)
def test_create_review_requires_the_portuguese_text(favorite, reviews, review_data):
    assert controller.create_and_save_movie_review("tt1", review_data)[1] == 400
    assert reviews.count_documents({}) == 0


def test_get_movie_review(reviews):
    reviews.insert_one({"tconst": "tt1", "content": REVIEW["content"]})

    body, status = controller.get_movie_review("tt1")

    assert status == 200
    assert body["total_documents"] == 1
    assert body["entries"][0]["tconst"] == "tt1"
    assert controller.get_movie_review("tt2")[1] == 404


def test_edit_movie_review_changes_only_the_editable_fields(reviews):
    reviews.insert_one({"tconst": "tt1", "content": REVIEW["content"], "images": []})

    body, status = controller.edit_movie_review(
        "tt1", {"images": ["1.jpg"], "tconst": "tt2", "isAiGenerated": True}
    )

    assert status == 200
    assert body["data"]["images"] == ["1.jpg"]
    assert body["data"]["tconst"] == "tt1"
    assert "isAiGenerated" not in body["data"]
    assert body["data"]["content"] == REVIEW["content"]


def test_edit_movie_review_is_404_when_missing():
    assert controller.edit_movie_review("tt1", {"images": []})[1] == 404


def test_delete_movie_review(reviews):
    reviews.insert_one({"tconst": "tt1"})

    assert controller.delete_movie_review("tt1")[1] == 200
    assert controller.delete_movie_review("tt1")[1] == 404


def test_get_created_reviews_lists_and_filters(reviews):
    reviews.insert_many(
        [
            {"tconst": "tt1", "isAiGenerated": True},
            {"tconst": "tt2", "isAiGenerated": False},
        ]
    )

    everything, status = controller.get_created_reviews()
    filtered, _ = controller.get_created_reviews({"isAiGenerated": True})

    assert status == 200
    assert everything["total_documents"] == 2
    assert [e["tconst"] for e in filtered["entries"]] == ["tt1"]
