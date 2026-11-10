from unittest.mock import Mock

import pytest

import config
from favorites import controller
from favorites.scrapper import IMDBUnavailable
from keywords.imdb import IMDBSearchError


@pytest.fixture
def imdb(monkeypatch):
    """Replaces everything favorite_movie asks IMDB and the translator."""
    mocks = Mock()
    mocks.get_movie_title.return_value = "The 400 Blows"
    mocks.collect_movie_data.return_value = {
        "plot": "A boy in Paris.",
        "startYear": 1959,
    }
    mocks.translate_movie.return_value = {"plot": "Um menino em Paris."}
    for name in ("get_movie_title", "collect_movie_data", "translate_movie"):
        monkeypatch.setattr(controller, name, getattr(mocks, name))
    return mocks


@pytest.fixture
def no_backfill(monkeypatch):
    monkeypatch.setattr(controller, "BACKFILLS", {})


# collect_movie_data


def test_collect_movie_data_keeps_only_the_fields_that_resolved(monkeypatch):
    def broken(tconst):
        raise ValueError("layout changed")

    monkeypatch.setattr(
        controller,
        "SCRAPERS",
        {
            "plot": lambda tconst: f"plot of {tconst}",
            "quote": lambda tconst: None,
            "trivia": lambda tconst: "",
            "genres": broken,
        },
    )
    monkeypatch.setattr(controller, "get_wikipedia_url", lambda title: f"wiki/{title}")
    clear = Mock()
    monkeypatch.setattr(controller, "clear_soup_cache", clear)

    data = controller.collect_movie_data("tt1", "Breathless")

    assert data == {"plot": "plot of tt1", "wiki": "wiki/Breathless"}
    clear.assert_called_once()


def test_collect_movie_data_gives_up_when_imdb_blocks(monkeypatch):
    after = Mock()

    def blocked(tconst):
        raise IMDBUnavailable("WAF")

    monkeypatch.setattr(controller, "SCRAPERS", {"plot": blocked, "quote": after})
    clear = Mock()
    monkeypatch.setattr(controller, "clear_soup_cache", clear)

    with pytest.raises(IMDBUnavailable):
        controller.collect_movie_data("tt1", "Breathless")

    after.assert_not_called()
    clear.assert_called_once()


# favorite_movie


def test_favorite_movie_saves_the_movie_with_its_translation(imdb, favorites):
    body, status = controller.favorite_movie("tt0053198")

    assert status == 201
    assert body["data"]["primaryTitle"] == "The 400 Blows"
    assert body["data"]["imdb_url"] == "https://www.imdb.com/title/tt0053198/"
    assert body["data"]["references"] == []
    # The answer is the English original, without the translations map.
    assert body["data"]["plot"] == "A boy in Paris."
    assert body["data"]["lang"] == "en"
    assert "translations" not in body["data"]

    stored = favorites.find_one({"tconst": "tt0053198"})
    assert stored["translations"] == {"pt": {"plot": "Um menino em Paris."}}
    assert stored["startYear"] == 1959


def test_favorite_movie_is_saved_even_when_the_translation_fails(imdb, favorites):
    imdb.translate_movie.return_value = None

    _, status = controller.favorite_movie("tt0053198")

    assert status == 201
    assert "translations" not in favorites.find_one({"tconst": "tt0053198"})


def test_favorite_movie_refuses_a_duplicate(imdb, favorites):
    favorites.insert_one({"tconst": "tt0053198"})

    assert controller.favorite_movie("tt0053198") == (
        {"message": "Movie already listed"},
        409,
    )
    imdb.get_movie_title.assert_not_called()


def test_favorite_movie_is_404_when_imdb_has_no_title(imdb, favorites):
    imdb.get_movie_title.return_value = None

    _, status = controller.favorite_movie("tt0000000")

    assert status == 404
    assert favorites.count_documents({}) == 0
    imdb.collect_movie_data.assert_not_called()


# get_favorited_movie


def test_get_favorited_movie_rejects_an_unknown_language():
    body, status = controller.get_favorited_movie("tt1", lang="es")

    assert status == 400
    assert "en, pt" in body["message"]


def test_get_favorited_movie_is_404_when_missing():
    assert controller.get_favorited_movie("tt1") == (
        {"message": "Movie not found"},
        404,
    )


def test_get_favorited_movie_applies_the_requested_language(favorites, no_backfill):
    favorites.insert_one(
        {
            "tconst": "tt1",
            "plot": "A boy.",
            "director": "François Truffaut",
            "translations": {"pt": {"plot": "Um menino."}},
        }
    )

    english = controller.get_favorited_movie("tt1")[0]["data"]
    portuguese = controller.get_favorited_movie("tt1", lang="pt")[0]["data"]

    assert (english["plot"], english["lang"]) == ("A boy.", "en")
    assert (portuguese["plot"], portuguese["lang"]) == ("Um menino.", "pt")
    assert portuguese["director"] == "François Truffaut"
    assert "translations" not in portuguese


def test_get_favorited_movie_answers_in_english_without_a_translation(
    favorites, no_backfill
):
    favorites.insert_one({"tconst": "tt1", "plot": "A boy."})

    movie = controller.get_favorited_movie("tt1", lang="pt")[0]["data"]

    assert (movie["plot"], movie["lang"]) == ("A boy.", "en")


def test_get_favorited_movie_backfills_the_missing_fields_once(favorites, monkeypatch):
    find_backdrop = Mock(return_value="https://img/backdrop.jpg")
    find_title = Mock(return_value=None)
    monkeypatch.setattr(
        controller,
        "BACKFILLS",
        {"backdrop_url": find_backdrop, "title_pt": find_title},
    )
    favorites.insert_one({"tconst": "tt1"})

    movie = controller.get_favorited_movie("tt1")[0]["data"]
    controller.get_favorited_movie("tt1")

    assert movie["backdrop_url"] == "https://img/backdrop.jpg"
    # "" is stored when IMDB has nothing, so it is not asked again.
    assert movie["title_pt"] == ""
    assert favorites.find_one({"tconst": "tt1"})["title_pt"] == ""
    find_backdrop.assert_called_once_with("tt1")
    find_title.assert_called_once_with("tt1")


def test_get_favorited_movie_retries_a_failed_backfill(favorites, monkeypatch):
    lookup = Mock(side_effect=IMDBSearchError("IMDB down"))
    monkeypatch.setattr(controller, "BACKFILLS", {"backdrop_url": lookup})
    favorites.insert_one({"tconst": "tt1"})

    body, status = controller.get_favorited_movie("tt1")
    controller.get_favorited_movie("tt1")

    assert status == 200
    assert "backdrop_url" not in body["data"]
    assert "backdrop_url" not in favorites.find_one({"tconst": "tt1"})
    assert lookup.call_count == 2


# translate_favorited_movie


def test_translate_favorited_movie_stores_the_translation(favorites, monkeypatch):
    monkeypatch.setattr(
        controller, "translate_movie", lambda movie: {"plot": "Um menino."}
    )
    favorites.insert_one({"tconst": "tt1", "plot": "A boy."})

    body, status = controller.translate_favorited_movie("tt1")

    assert status == 200
    assert (body["data"]["plot"], body["data"]["lang"]) == ("Um menino.", "pt")
    assert favorites.find_one({"tconst": "tt1"})["translations"] == {
        "pt": {"plot": "Um menino."}
    }


def test_translate_favorited_movie_is_404_when_missing():
    assert controller.translate_favorited_movie("tt1")[1] == 404


def test_translate_favorited_movie_is_502_when_the_translator_fails(
    favorites, monkeypatch
):
    monkeypatch.setattr(controller, "translate_movie", lambda movie: None)
    favorites.insert_one({"tconst": "tt1", "plot": "A boy."})

    assert controller.translate_favorited_movie("tt1")[1] == 502
    assert "translations" not in favorites.find_one({"tconst": "tt1"})


# edit_favorited_movie / sync_blogpost


def test_edit_favorited_movie_changes_only_the_editable_fields(favorites):
    favorites.insert_one({"tconst": "tt1", "primaryTitle": "Breathless", "wiki": "old"})

    body, status = controller.edit_favorited_movie(
        "tt1", {"watched": True, "primaryTitle": "Hacked", "tconst": "tt2"}
    )

    assert status == 200
    assert body["data"]["watched"] is True
    assert body["data"]["primaryTitle"] == "Breathless"
    assert body["data"]["tconst"] == "tt1"
    assert body["data"]["wiki"] == "old"


def test_edit_favorited_movie_is_404_when_missing():
    body, status = controller.edit_favorited_movie("tt1", {"watched": True})

    assert status == 404
    assert "tt1" in body["message"]


def test_edit_favorited_movie_mirrors_fields_onto_the_blogpost(favorites, mongo):
    blogposts = mongo[config.BLOGPOSTS_COLLECTION]
    favorites.insert_one({"tconst": "tt1"})
    blogposts.insert_one({"tconst": "tt1", "title": "Post"})

    controller.edit_favorited_movie(
        "tt1", {"soundtrack": "spotify:album:1", "references": ["a"], "watched": True}
    )

    assert blogposts.find_one({"tconst": "tt1"}, {"_id": 0}) == {
        "tconst": "tt1",
        "title": "Post",
        "spotify_album_url": "spotify:album:1",
        "references": ["a"],
    }


def test_edit_favorited_movie_does_not_create_a_blogpost(favorites, mongo):
    favorites.insert_one({"tconst": "tt1"})

    controller.edit_favorited_movie("tt1", {"soundtrack": "spotify:album:1"})

    assert mongo[config.BLOGPOSTS_COLLECTION].count_documents({}) == 0


def test_edit_favorited_movie_succeeds_when_the_blogpost_sync_fails(
    favorites, monkeypatch
):
    favorites.insert_one({"tconst": "tt1"})
    real = controller.get_mongo_collection

    def failing(name):
        if name == config.BLOGPOSTS_COLLECTION:
            raise RuntimeError("boom")
        return real(name)

    monkeypatch.setattr(controller, "get_mongo_collection", failing)

    body, status = controller.edit_favorited_movie("tt1", {"soundtrack": "url"})

    assert status == 200
    assert body["data"]["soundtrack"] == "url"


# delete_favorited_movie


def test_delete_favorited_movie(favorites):
    favorites.insert_one({"tconst": "tt1"})

    assert controller.delete_favorited_movie("tt1")[1] == 200
    assert controller.delete_favorited_movie("tt1")[1] == 404
    assert favorites.count_documents({}) == 0


# get_favorited_movies


@pytest.fixture
def catalog(favorites):
    favorites.insert_many(
        [
            {
                "tconst": "tt0053198",
                "primaryTitle": "The 400 Blows",
                "director": "François Truffaut",
                "country": "France",
                "startYear": 1959,
                "trivia": "long text",
            },
            {
                "tconst": "tt0053472",
                "primaryTitle": "Breathless",
                "director": "Jean-Luc Godard",
                "country": "France",
                "startYear": "1960",
            },
            {
                "tconst": "tt0050976",
                "primaryTitle": "The Seventh Seal",
                "director": "Ingmar Bergman",
                "country": "Sweden",
                "startYear": None,
            },
        ]
    )
    return favorites


def titles(body):
    return {entry["primaryTitle"] for entry in body["entries"]}


def test_get_favorited_movies_lists_everything_with_the_filter_options(catalog):
    body, status = controller.get_favorited_movies()

    assert status == 200
    assert body["total_documents"] == 3
    assert sorted(body["countries"]) == ["France", "Sweden"]
    assert sorted(body["years"]) == [1959, 1960]


def test_get_favorited_movies_returns_only_the_list_fields(catalog):
    body, _ = controller.get_favorited_movies(search_term="tt0053198")

    assert set(body["entries"][0]) == {"_id", "primaryTitle", "startYear", "tconst"}


@pytest.mark.parametrize(
    "term, expected",
    [
        ("tt0053472", {"Breathless"}),
        ("the", {"The 400 Blows", "The Seventh Seal"}),
        ("godard", {"Breathless"}),
        ("nothing like it", set()),
    ],
)
def test_get_favorited_movies_search_term(catalog, term, expected):
    body, _ = controller.get_favorited_movies(search_term=term)

    assert titles(body) == expected
    assert body["total_documents"] == len(expected)


def test_get_favorited_movies_accepts_the_search_term_inside_filters(catalog):
    body, _ = controller.get_favorited_movies(filters={"search_term": "bergman"})
    assert titles(body) == {"The Seventh Seal"}


def test_get_favorited_movies_combines_search_term_and_filters(catalog):
    body, _ = controller.get_favorited_movies(
        filters={"country": "France"}, search_term="the"
    )
    assert titles(body) == {"The 400 Blows"}


def test_get_favorited_movies_leaves_tconst_operators_alone(catalog):
    body, _ = controller.get_favorited_movies(
        filters={"tconst": {"$in": ["tt0053198", "tt0050976"]}}
    )
    assert titles(body) == {"The 400 Blows", "The Seventh Seal"}


def test_get_favorited_movies_paginates(catalog):
    body, _ = controller.get_favorited_movies(page=2, page_size=2)

    assert body["total_documents"] == 3
    assert len(body["entries"]) == 1


def test_get_favorited_movies_does_not_mutate_the_request_filters(catalog):
    filters = {"search_term": "the"}
    controller.get_favorited_movies(filters=filters)
    assert filters == {"search_term": "the"}
