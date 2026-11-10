from unittest.mock import Mock

import pytest

from keywords import controller
from keywords.imdb import IMDBSearchError


def movie(tconst):
    return {"tconst": tconst, "title": f"Movie {tconst}"}


@pytest.fixture
def imdb(monkeypatch):
    """Keyword and director searches answered from two dicts."""
    mocks = Mock()
    mocks.by_keyword = {}
    mocks.by_director = {}
    mocks.search_movies_by_keyword.side_effect = (
        lambda keyword, first: mocks.by_keyword.get(keyword, [])
    )
    mocks.search_movies_by_director.side_effect = (
        lambda name, first: mocks.by_director.get(name, [])
    )
    for name in ("search_movies_by_keyword", "search_movies_by_director"):
        monkeypatch.setattr(controller, name, getattr(mocks, name))
    return mocks


def test_add_keyword_strips_and_saves():
    body, status = controller.add_keyword("  nouvelle vague ")

    assert status == 201
    assert body["data"]["keyword"] == "nouvelle vague"


@pytest.mark.parametrize("keyword", [None, "", "   "])
def test_add_keyword_requires_a_keyword(keyword):
    assert controller.add_keyword(keyword)[1] == 400


def test_add_keyword_refuses_a_duplicate():
    controller.add_keyword("noir")
    assert controller.add_keyword(" noir ")[1] == 409


def test_get_favorited_keywords_is_sorted():
    for keyword in ("noir", "heist", "road movie"):
        controller.add_keyword(keyword)

    body, status = controller.get_favorited_keywords()

    assert status == 200
    assert [k["keyword"] for k in body["data"]] == ["heist", "noir", "road movie"]


def test_delete_favorited_keyword():
    controller.add_keyword("noir")

    assert controller.delete_favorited_keyword("noir")[1] == 200
    assert controller.delete_favorited_keyword("noir")[1] == 404


def test_suggest_ranks_movies_matching_more_keywords_first(imdb):
    imdb.by_keyword = {
        "noir": [movie("tt1"), movie("tt2"), movie("tt3")],
        "heist": [movie("tt3"), movie("tt4")],
    }

    body, status = controller.suggest_movies_by_keywords(["noir", "heist"])

    assert status == 200
    movies = body["data"]["movies"]
    # tt3 matches both; the others are ordered by their position on IMDB.
    assert [m["tconst"] for m in movies] == ["tt3", "tt1", "tt2", "tt4"]
    assert movies[0]["relevance"] == "Palavras-chave no IMDb: noir, heist"
    assert movies[1]["relevance"] == "Palavras-chave no IMDb: noir"


def test_suggest_prefers_the_movies_of_a_director(imdb):
    imdb.by_director = {"François Truffaut": [movie("tt1")]}
    imdb.by_keyword = {"François Truffaut": [movie("tt9")]}

    body, _ = controller.suggest_movies_by_keywords(["François Truffaut"])

    assert [m["tconst"] for m in body["data"]["movies"]] == ["tt1"]
    imdb.search_movies_by_keyword.assert_not_called()


def test_suggest_ignores_blank_and_repeated_keywords(imdb):
    imdb.by_keyword = {"noir": [movie("tt1")]}

    body, _ = controller.suggest_movies_by_keywords(["noir", " noir ", "", "  "])

    assert body["data"]["movies"][0]["relevance"] == "Palavras-chave no IMDb: noir"
    assert imdb.search_movies_by_director.call_count == 1


def test_suggest_limits_the_answer(imdb):
    imdb.by_keyword = {
        "noir": [movie(f"tt{n}") for n in range(controller.SUGGESTION_LIMIT + 5)]
    }

    body, _ = controller.suggest_movies_by_keywords(["noir"])

    assert len(body["data"]["movies"]) == controller.SUGGESTION_LIMIT


def test_suggest_is_empty_for_keywords_imdb_does_not_know(imdb):
    assert controller.suggest_movies_by_keywords(["zzz"]) == (
        {"data": {"movies": []}},
        200,
    )
    assert controller.suggest_movies_by_keywords([])[1] == 200


def test_suggest_survives_a_keyword_that_fails(imdb):
    def by_keyword(keyword, first):
        if keyword == "broken":
            raise IMDBSearchError("timeout")
        return [movie("tt1")]

    imdb.search_movies_by_keyword.side_effect = by_keyword

    body, status = controller.suggest_movies_by_keywords(["broken", "noir"])

    assert status == 200
    assert [m["tconst"] for m in body["data"]["movies"]] == ["tt1"]


def test_suggest_is_502_when_every_search_fails(imdb):
    imdb.search_movies_by_director.side_effect = IMDBSearchError("timeout")

    assert controller.suggest_movies_by_keywords(["noir", "heist"])[1] == 502
