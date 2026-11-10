from unittest.mock import Mock

import pytest

from belas_artes import controller
from belas_artes.catalog import CatalogUnavailable
from keywords.imdb import IMDBSearchError


def title(title_id, name, original="", year=1960):
    return {
        "id": title_id,
        "title": f" {name} ",
        "original_title": original,
        "year": year,
        "director": " Jean-Luc Godard ",
    }


CATALOG = {
    "views": {
        "1": {"slug": "home", "lists": []},
        "2": {
            "slug": controller.RECENT_VIEW,
            "lists": [
                {"type": "BANNERS", "items": [99]},
                {"type": "GRID", "items": [10, 20]},
                # 10 repeats and 30 is not in the catalog.
                {"type": "GRID", "items": [10, 30]},
            ],
        },
    },
    "titles": {
        "10": title(10, "Acossado", "À bout de souffle"),
        "20": title(20, "Alphaville", year=1965),
        "99": title(99, "Banner"),
    },
}


@pytest.fixture
def find_rating(monkeypatch):
    mock = Mock(return_value={"tconst": "tt0053472", "rating": 7.7})
    monkeypatch.setattr(controller, "find_rating", mock)
    monkeypatch.setattr(controller, "_ratings", {})
    monkeypatch.setattr(controller, "load_catalog", lambda: CATALOG)
    return mock


def test_recently_added_lists_the_grid_titles_with_the_rating(find_rating):
    find_rating.side_effect = lambda name, year: (
        {"tconst": "tt0053472", "rating": 7.7} if year == 1960 else None
    )

    body, status = controller.get_recently_added()

    assert status == 200
    assert body["data"]["movies"] == [
        {
            "id": 10,
            "title": "Acossado",
            "original_title": "À bout de souffle",
            "year": 1960,
            "director": "Jean-Luc Godard",
            "tconst": "tt0053472",
            "imdb_rating": 7.7,
        },
        {
            "id": 20,
            "title": "Alphaville",
            "original_title": "",
            "year": 1965,
            "director": "Jean-Luc Godard",
            "tconst": None,
            "imdb_rating": None,
        },
    ]


def test_recently_added_searches_by_original_title_when_there_is_one(find_rating):
    controller.get_recently_added()

    assert sorted(call.args for call in find_rating.call_args_list) == [
        (" Alphaville ", 1965),
        ("À bout de souffle", 1960),
    ]


def test_recently_added_caches_the_ratings(find_rating):
    controller.get_recently_added()
    controller.get_recently_added()

    assert find_rating.call_count == 2


def test_recently_added_asks_again_after_the_cache_expires(find_rating, monkeypatch):
    controller.get_recently_added()
    for cached in controller._ratings.values():
        cached["at"] -= controller.RATING_TTL + 1

    controller.get_recently_added()

    assert find_rating.call_count == 4


def test_recently_added_does_not_cache_an_imdb_failure(find_rating):
    find_rating.side_effect = IMDBSearchError("timeout")

    body, status = controller.get_recently_added()
    controller.get_recently_added()

    assert status == 200
    assert [m["imdb_rating"] for m in body["data"]["movies"]] == [None, None]
    assert find_rating.call_count == 4


def test_recently_added_is_502_when_the_catalog_is_down(find_rating, monkeypatch):
    def down():
        raise CatalogUnavailable("timeout")

    monkeypatch.setattr(controller, "load_catalog", down)

    assert controller.get_recently_added()[1] == 502
    find_rating.assert_not_called()


def test_recently_added_is_404_when_the_section_is_gone(find_rating, monkeypatch):
    monkeypatch.setattr(controller, "load_catalog", lambda: {"views": {}, "titles": {}})

    assert controller.get_recently_added()[1] == 404
