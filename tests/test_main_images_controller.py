import io
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from werkzeug.datastructures import FileStorage

import config
from main_images import controller


@pytest.fixture
def s3(monkeypatch):
    """Fake S3 client; the image is uploaded as is, without Pillow."""
    client = Mock()
    monkeypatch.setattr(controller, "s3_client", lambda: client)
    monkeypatch.setattr(controller, "optimize_image", lambda file, **kwargs: file)
    return client


@pytest.fixture
def images(mongo):
    return mongo[config.MAIN_IMAGES_COLLECTION]


def upload(filename="Poster.JPG", **subtitles):
    file = FileStorage(stream=io.BytesIO(b"image bytes"), filename=filename)
    return controller.upload_image_to_s3(file, "tt1", **subtitles)


def test_s3_client_requires_the_credentials(monkeypatch):
    monkeypatch.setattr(controller, "AWS_ACCESS_KEY_ID", None)

    with pytest.raises(controller.StorageUnavailable):
        controller.s3_client()


def test_s3_client_uses_the_configured_credentials(monkeypatch):
    boto3 = Mock()
    monkeypatch.setattr(controller, "boto3", boto3)
    monkeypatch.setattr(controller, "AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setattr(controller, "AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(controller, "AWS_REGION", "us-east-2")

    assert controller.s3_client() is boto3.client.return_value
    boto3.client.assert_called_once_with(
        "s3",
        aws_access_key_id="key",
        aws_secret_access_key="secret",
        region_name="us-east-2",
    )


def test_upload_names_the_object_by_sequential_id(s3, images):
    body, status = upload()

    assert status == 200
    assert body["filename"] == "1.jpg"
    assert body["sequential_id"] == 1
    assert body["object_name"] == "main-images/tt1/1.jpg"

    _, bucket, key = s3.upload_fileobj.call_args.args
    assert (bucket, key) == (controller.S3_BUCKET, "main-images/tt1/1.jpg")
    assert s3.upload_fileobj.call_args.kwargs == {
        "ExtraArgs": {"ContentType": "image/jpeg"}
    }
    stored = images.find_one({"tconst": "tt1"})
    assert (stored["filename"], stored["sequential_id"]) == ("1.jpg", 1)


def test_upload_continues_the_sequence_of_the_movie(s3, images):
    images.insert_one({"tconst": "tt1", "filename": "4.jpg", "sequential_id": 4})
    images.insert_one({"tconst": "tt2", "filename": "9.jpg", "sequential_id": 9})

    assert upload("still.png")[0]["filename"] == "5.png"
    assert upload("still.png")[0]["filename"] == "6.png"


def test_upload_tags_the_object_only_when_there_are_subtitles(s3, images):
    upload()
    s3.put_object_tagging.assert_not_called()

    upload(subtitle_en="Antoine, at the beach!", subtitle_pt="Antoine na praia")

    assert s3.put_object_tagging.call_args.kwargs == {
        "Bucket": controller.S3_BUCKET,
        "Key": "main-images/tt1/2.jpg",
        "Tagging": {
            "TagSet": [
                {"Key": "subtitle_en", "Value": "Antoine at the beach"},
                {"Key": "subtitle_pt", "Value": "Antoine na praia"},
            ]
        },
    }
    # Mongo keeps the subtitle as typed; only the S3 tag is sanitized.
    assert (
        images.find_one({"sequential_id": 2})["subtitle_en"] == "Antoine, at the beach!"
    )


def test_upload_is_500_and_stores_nothing_when_s3_fails(s3, images):
    s3.upload_fileobj.side_effect = RuntimeError("network")

    body, status = upload()

    assert (body, status) == ({"message": "Erro ao fazer upload para S3"}, 500)
    assert images.count_documents({}) == 0


def test_upload_without_credentials_raises_storage_unavailable(monkeypatch, images):
    monkeypatch.setattr(controller, "AWS_SECRET_ACCESS_KEY", "")

    with pytest.raises(controller.StorageUnavailable):
        upload()


def test_get_all_image_urls_lists_in_sequence_with_public_urls(images, monkeypatch):
    monkeypatch.setattr(controller, "S3_BUCKET", "bucket")
    monkeypatch.setattr(controller, "AWS_REGION", "us-east-2")
    images.insert_many(
        [
            {"tconst": "tt1", "filename": "2.png", "sequential_id": 2},
            {
                "tconst": "tt1",
                "filename": "1.jpg",
                "sequential_id": 1,
                "subtitle_en": "Beach",
                "subtitle_pt": "Praia",
            },
            {"tconst": "tt2", "filename": "1.jpg", "sequential_id": 1},
        ]
    )

    body, status = controller.get_all_image_urls("tt1")

    assert status == 200
    assert body["images"] == [
        {
            "url": "https://bucket.s3.us-east-2.amazonaws.com/main-images/tt1/1.jpg",
            "filename": "1.jpg",
            "sequential_id": 1,
            "subtitle_en": "Beach",
            "subtitle_pt": "Praia",
        },
        {
            "url": "https://bucket.s3.us-east-2.amazonaws.com/main-images/tt1/2.png",
            "filename": "2.png",
            "sequential_id": 2,
            "subtitle_en": "",
            "subtitle_pt": "",
        },
    ]


def test_get_all_image_urls_is_empty_for_a_movie_without_images():
    assert controller.get_all_image_urls("tt1") == ({"images": []}, 200)


def test_delete_image_removes_the_object_and_its_metadata(s3, images):
    images.insert_one({"tconst": "tt1", "filename": "1.jpg", "sequential_id": 1})
    images.insert_one({"tconst": "tt1", "filename": "2.jpg", "sequential_id": 2})

    _, status = controller.delete_image_from_s3("tt1", "1.jpg")

    assert status == 200
    s3.delete_object.assert_called_once_with(
        Bucket=controller.S3_BUCKET, Key="main-images/tt1/1.jpg"
    )
    assert [doc["filename"] for doc in images.find()] == ["2.jpg"]


def test_delete_image_keeps_the_metadata_when_s3_fails(s3, images):
    images.insert_one({"tconst": "tt1", "filename": "1.jpg", "sequential_id": 1})
    s3.delete_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "denied"}}, "DeleteObject"
    )

    assert controller.delete_image_from_s3("tt1", "1.jpg")[1] == 500
    assert images.count_documents({}) == 1


def test_sanitize_tag_value_drops_what_s3_tags_refuse():
    assert (
        controller.sanitize_tag_value("Olá, mundo! (1959) - fim")
        == "Olá mundo 1959 - fim"
    )


def test_sanitize_tag_value_cuts_long_values_at_a_word():
    sanitized = controller.sanitize_tag_value("palavra " * 60)

    assert len(sanitized) <= 256
    assert sanitized.endswith("palavra")


def test_sanitize_tag_value_cuts_a_single_long_word():
    assert controller.sanitize_tag_value("a" * 300) == "a" * 256
