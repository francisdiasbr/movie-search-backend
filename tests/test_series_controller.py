from unittest.mock import Mock

import pytest

import config
from keywords.imdb import IMDBSearchError
from series import controller


def found_series(**overrides):
    return {
        "tconst": "tt0903747",
        "primaryTitle": "Breaking Bad",
        "startYear": 2008,
        "seasons": 5,
        "plot": "A chemistry teacher.",
        "is_series": True,
        **overrides,
    }


@pytest.fixture
def series(mongo):
    return mongo[config.SERIES_COLLECTION]


@pytest.fixture
def imdb(monkeypatch):
    mocks = Mock()
    mocks.find_series.return_value = found_series()
    mocks.find_brazilian_title.return_value = "Breaking Bad: A Química do Mal"
    monkeypatch.setattr(controller, "find_series", mocks.find_series)
    monkeypatch.setattr(controller, "find_brazilian_title", mocks.find_brazilian_title)
    return mocks


def test_add_series_saves_what_imdb_says(imdb, series):
    body, status = controller.add_series("tt0903747")

    assert status == 201
    assert body["data"]["primaryTitle"] == "Breaking Bad"
    assert body["data"]["title_pt"] == "Breaking Bad: A Química do Mal"
    assert body["data"]["imdb_url"] == "https://www.imdb.com/title/tt0903747/"
    assert body["data"]["watched"] is False
    assert "is_series" not in body["data"]
    assert series.count_documents({"tconst": "tt0903747"}) == 1


def test_add_series_stores_an_empty_brazilian_title_when_there_is_none(imdb):
    imdb.find_brazilian_title.return_value = None
    assert controller.add_series("tt0903747")[0]["data"]["title_pt"] == ""


def test_add_series_refuses_a_duplicate(imdb, series):
    series.insert_one({"tconst": "tt0903747"})

    assert controller.add_series("tt0903747")[1] == 409
    imdb.find_series.assert_not_called()


def test_add_series_is_404_when_imdb_does_not_know_the_title(imdb, series):
    imdb.find_series.return_value = None

    assert controller.add_series("tt0000000")[1] == 404
    imdb.find_brazilian_title.assert_not_called()
    assert series.count_documents({}) == 0


def test_add_series_refuses_a_movie(imdb, series):
    imdb.find_series.return_value = found_series(is_series=False)

    assert controller.add_series("tt0903747")[1] == 400
    assert series.count_documents({}) == 0


@pytest.mark.parametrize("failing", ["find_series", "find_brazilian_title"])
def test_add_series_is_502_when_imdb_fails(imdb, series, failing):
    getattr(imdb, failing).side_effect = IMDBSearchError("timeout")

    assert controller.add_series("tt0903747")[1] == 502
    assert series.count_documents({}) == 0


def test_get_series(series):
    series.insert_one({"tconst": "tt1", "plot": "Full document."})

    body, status = controller.get_series("tt1")

    assert status == 200
    assert body["data"]["plot"] == "Full document."
    assert controller.get_series("tt2")[1] == 404


@pytest.fixture
def listed(series):
    series.insert_many(
        [
            {
                "tconst": "tt3",
                "primaryTitle": "The Wire",
                "title_pt": "A Escuta",
                "plot": "x",
            },
            {
                "tconst": "tt1",
                "primaryTitle": "Breaking Bad",
                "title_pt": "",
                "watched": True,
            },
            {
                "tconst": "tt2",
                "primaryTitle": "Mad Men",
                "title_pt": "",
                "watched": False,
            },
        ]
    )


def test_list_series_sorts_by_title_and_hides_the_detail_fields(listed):
    body, status = controller.list_series()

    assert status == 200
    assert body["total_documents"] == 3
    assert [e["primaryTitle"] for e in body["entries"]] == [
        "Breaking Bad",
        "Mad Men",
        "The Wire",
    ]
    assert "plot" not in body["entries"][2]


@pytest.mark.parametrize(
    "term, expected",
    [
        ("tt2", ["Mad Men"]),
        ("WIRE", ["The Wire"]),
        ("escuta", ["The Wire"]),
        ("zzz", []),
    ],
)
def test_list_series_search_term(listed, term, expected):
    body, _ = controller.list_series(search_term=term)
    assert [e["primaryTitle"] for e in body["entries"]] == expected


def test_list_series_filters_and_paginates(listed):
    watched, _ = controller.list_series(filters={"watched": True})
    second_page, _ = controller.list_series(page=2, page_size=2)

    assert [e["tconst"] for e in watched["entries"]] == ["tt1"]
    assert second_page["total_documents"] == 3
    assert [e["tconst"] for e in second_page["entries"]] == ["tt3"]


def test_edit_series_only_changes_watched(series):
    series.insert_one({"tconst": "tt1", "primaryTitle": "Mad Men", "watched": False})

    body, status = controller.edit_series("tt1", {"watched": True, "primaryTitle": "x"})

    assert status == 200
    assert body["data"]["watched"] is True
    assert body["data"]["primaryTitle"] == "Mad Men"
    assert controller.edit_series("tt9", {"watched": True})[1] == 404


def test_delete_series(series):
    series.insert_one({"tconst": "tt1"})

    assert controller.delete_series("tt1")[1] == 200
    assert controller.delete_series("tt1")[1] == 404
