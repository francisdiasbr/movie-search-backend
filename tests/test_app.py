"""The Flask app end to end: routing, body parsing and the 503 handlers."""

import pytest

import config
from app import app
from favorites.scrapper import IMDBUnavailable
from main_images.controller import StorageUnavailable


@pytest.fixture
def client():
    return app.test_client()


def test_home_reports_the_api_online(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json["status"] == "online"


def test_keyword_round_trip_through_the_routes(client):
    created = client.post("/api/keywords/", json={"keyword": "noir"})
    duplicate = client.post("/api/keywords/", json={"keyword": "noir"})
    listed = client.get("/api/keywords/")
    deleted = client.delete("/api/keywords/noir")

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json == {"message": "Keyword already listed"}
    assert [k["keyword"] for k in listed.json["data"]] == ["noir"]
    assert deleted.status_code == 200


def test_swagger_model_validates_the_body(client, mongo):
    mongo[config.SERIES_COLLECTION].insert_one({"tconst": "tt1", "watched": False})

    wrong_type = client.put("/api/series/tt1", json={"watched": "yes"})
    not_an_object = client.put("/api/series/tt1", json=["watched"])
    empty = client.put("/api/series/tt1", json={})

    assert wrong_type.status_code == 400
    assert not_an_object.status_code == 400
    assert "message" in wrong_type.json
    # No field sent is a valid, idempotent edit.
    assert empty.status_code == 200
    assert empty.json["data"]["watched"] is False


def test_unknown_route_is_404_with_a_message(client):
    response = client.get("/api/nothing-here")

    assert response.status_code == 404
    assert "message" in response.json


def test_database_down_is_503(client, monkeypatch):
    def down():
        raise config.DatabaseUnavailable("MongoDB Atlas indisponível")

    monkeypatch.setattr(config, "get_mongo_client", down)

    response = client.get("/api/series/tt1")

    assert response.status_code == 503
    assert response.json == {"message": "MongoDB Atlas indisponível"}


def test_storage_without_credentials_is_503(client, monkeypatch):
    def unavailable():
        raise StorageUnavailable("Credenciais AWS não configuradas")

    monkeypatch.setattr("main_images.controller.s3_client", unavailable)

    response = client.delete("/api/main-images/tt1/1.jpg")

    assert response.status_code == 503
    assert response.json == {"message": "Credenciais AWS não configuradas"}


def test_blocked_imdb_is_503_and_not_404(client, monkeypatch):
    def blocked(tconst):
        raise IMDBUnavailable("IMDB bloqueou o acesso")

    monkeypatch.setattr("favorites.controller.get_movie_title", blocked)

    response = client.post("/api/favorites/tt0053198")

    assert response.status_code == 503
    assert response.json == {"message": "IMDB bloqueou o acesso"}


def test_upload_without_a_file_is_400(client):
    response = client.post("/api/main-images/tt1", data={})
    assert response.status_code == 400


# Every route that declares a Swagger model with @api.expect. flask-restx
# validates the body before the resource runs, so these answers never reach
# utils.json_body().
ROUTES_WITH_A_BODY = [
    ("post", "/api/favorites/search"),
    ("put", "/api/favorites/tt1"),
    ("post", "/api/keywords/"),
    ("post", "/api/keywords/suggest-movies"),
    ("post", "/api/write-review/tt1"),
    ("put", "/api/write-review/tt1"),
    ("post", "/api/write-review/search"),
    ("post", "/api/series/search"),
    ("put", "/api/series/tt1"),
]


@pytest.mark.parametrize("method, url", ROUTES_WITH_A_BODY)
def test_request_without_a_json_body_is_415(client, method, url):
    response = getattr(client, method)(url)

    assert response.status_code == 415
    assert set(response.json) == {"message"}


@pytest.mark.parametrize("method, url", ROUTES_WITH_A_BODY)
def test_malformed_json_is_400(client, method, url):
    response = getattr(client, method)(
        url, data="{not json", content_type="application/json"
    )

    assert response.status_code == 400
    assert set(response.json) == {"message"}
