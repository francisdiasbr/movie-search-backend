import io

from flask import Flask
from PIL import Image

import utils


def make_image(width, height, fmt="JPEG", mode="RGB"):
    buffer = io.BytesIO()
    Image.new(mode, (width, height), "red").save(buffer, format=fmt)
    buffer.seek(0)
    return buffer


def test_error_has_the_single_error_shape():
    assert utils.error("Não encontrado", 404) == ({"message": "Não encontrado"}, 404)


def test_json_body_returns_the_object_sent():
    with Flask(__name__).test_request_context(json={"watched": True}):
        assert utils.json_body() == {"watched": True}


def test_json_body_is_empty_dict_when_body_is_not_an_object():
    app = Flask(__name__)
    with app.test_request_context(json=["a", "b"]):
        assert utils.json_body() == {}
    with app.test_request_context(data="not json", content_type="application/json"):
        assert utils.json_body() == {}
    with app.test_request_context():
        assert utils.json_body() == {}


def test_pick_keeps_only_allowed_keys():
    data = {"watched": True, "tconst": "tt1", "wiki": None}
    assert utils.pick(data, ("watched", "wiki", "soundtrack")) == {
        "watched": True,
        "wiki": None,
    }


def test_pick_accepts_non_dict():
    assert utils.pick(None, ("watched",)) == {}
    assert utils.pick(["watched"], ("watched",)) == {}


def test_sanitize_movie_data_replaces_nan_and_inf_at_any_depth():
    movie = {
        "rating": float("nan"),
        "votes": float("inf"),
        "year": 1959,
        "nested": {"score": float("-inf"), "ok": 1.5},
        "items": [{"value": float("nan")}, "text", 3],
    }

    assert utils.sanitize_movie_data(movie) == {
        "rating": None,
        "votes": None,
        "year": 1959,
        "nested": {"score": None, "ok": 1.5},
        "items": [{"value": None}, "text", 3],
    }


def test_sanitize_filters_rejects_non_dict():
    assert utils.sanitize_filters(None) == {}
    assert utils.sanitize_filters("tt1") == {}


def test_sanitize_filters_turns_regex_into_string():
    filters = {
        "primaryTitle": {"$regex": 400, "$options": "i"},
        "director": {"$regex": None},
        "watched": True,
    }

    assert utils.sanitize_filters(filters) == {
        "primaryTitle": {"$regex": "400", "$options": "i"},
        "director": {"$regex": ""},
        "watched": True,
    }


def test_sanitize_filters_goes_into_or_conditions():
    filters = {"$or": [{"primaryTitle": {"$regex": 8}}, {"tconst": "tt1"}, "raw"]}

    assert utils.sanitize_filters(filters) == {
        "$or": [{"primaryTitle": {"$regex": "8"}}, {"tconst": "tt1"}, "raw"]
    }


def test_sanitize_filters_does_not_mutate_the_input():
    filters = {"primaryTitle": {"$regex": 400}}
    utils.sanitize_filters(filters)
    assert filters == {"primaryTitle": {"$regex": 400}}


def test_optimize_image_resizes_keeping_the_aspect_ratio():
    optimized = Image.open(utils.optimize_image(make_image(1600, 1200)))

    assert optimized.size == (800, 600)
    assert optimized.format == "JPEG"


def test_optimize_image_does_not_upscale():
    optimized = Image.open(utils.optimize_image(make_image(400, 300)))
    assert optimized.size == (400, 300)


def test_optimize_image_respects_max_width():
    optimized = Image.open(utils.optimize_image(make_image(1000, 500), max_width=200))
    assert optimized.size == (200, 100)


def test_optimize_image_keeps_png_as_png():
    optimized = Image.open(utils.optimize_image(make_image(1000, 500, "PNG", "RGBA")))

    assert optimized.format == "PNG"
    assert optimized.size == (800, 400)


def test_optimize_image_saves_other_formats_as_jpeg():
    optimized = Image.open(utils.optimize_image(make_image(1000, 500, "BMP")))
    assert optimized.format == "JPEG"


def test_optimize_image_returns_the_stream_rewound():
    assert utils.optimize_image(make_image(1000, 500)).tell() == 0


def test_optimize_image_gives_back_the_original_file_when_it_is_not_an_image():
    broken = io.BytesIO(b"definitely not an image")
    broken.seek(5)

    result = utils.optimize_image(broken)

    assert result is broken
    assert result.tell() == 5
