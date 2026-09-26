import io

import pytest
from PIL import Image, PngImagePlugin

from backend.app.errors import AppError
from backend.app.images import MAX_UPLOAD_BYTES, sanitize_image


def test_upload_is_private_and_project_tracks_source(client, project, source):
    response = client.get(source["url"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert len(response.content) == source["bytes"]
    assert client.get(f"/api/projects/{project['id']}").json()["source_asset_id"] == source["id"]
    assert client.get("/assets/" + source["id"]).status_code == 404


@pytest.mark.parametrize(
    "image_format,extension,mime", [("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg")]
)
def test_upload_strips_exif_and_metadata_preserving_orientation(
    client, project, image_format, extension, mime
):
    stream = io.BytesIO()
    picture = Image.new("RGB", (30, 20), "teal")
    exif = Image.Exif()
    exif[274] = 6
    exif[315] = "Sensitive author"
    options = {"exif": exif}
    if image_format == "PNG":
        text = PngImagePlugin.PngInfo()
        text.add_text("Comment", "Private location")
        options["pnginfo"] = text
    picture.save(stream, image_format, **options)
    response = client.post(
        f"/api/projects/{project['id']}/images",
        files={"file": (f"input.{extension}", stream.getvalue(), mime)},
    )
    assert response.status_code == 201
    downloaded = client.get(response.json()["url"])
    with Image.open(io.BytesIO(downloaded.content)) as clean:
        assert clean.size == (20, 30)
        assert not clean.getexif()
        assert "Comment" not in clean.info
    assert b"Sensitive author" not in downloaded.content
    assert b"Private location" not in downloaded.content


@pytest.mark.parametrize("size", [(4097, 10), (4096, 4096)])
def test_rejects_edge_and_total_pixel_limits(client, project, size):
    stream = io.BytesIO()
    Image.new("RGB", size, "white").save(stream, "PNG")
    response = client.post(
        f"/api/projects/{project['id']}/images",
        files={"file": ("large.png", stream.getvalue(), "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "image_dimensions_exceeded"
    assert client.get(f"/api/projects/{project['id']}").json()["source_asset_id"] is None


def test_accepts_dimension_boundaries():
    for size in [(4096, 10), (4000, 4000)]:
        stream = io.BytesIO()
        Image.new("RGB", size, "white").save(stream, "PNG")
        assert sanitize_image(stream.getvalue(), "boundary.png", "image/png").mime == "image/png"


def test_rejects_upload_over_byte_limit(client, project):
    response = client.post(
        f"/api/projects/{project['id']}/images",
        files={"file": ("large.png", b"x" * (MAX_UPLOAD_BYTES + 1), "image/png")},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "image_too_large"
    assert response.json()["request_id"]


def test_rejects_chunked_body_over_limit(client, project):
    def body():
        yield (
            b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="big.png"'
            b"\r\nContent-Type: image/png\r\n\r\n"
        )
        for _ in range(12):
            yield b"x" * 1024 * 1024
        yield b"\r\n--boundary--\r\n"

    response = client.post(
        f"/api/projects/{project['id']}/images",
        content=body(),
        headers={"Content-Type": "multipart/form-data; boundary=boundary"},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "image_too_large"


@pytest.mark.parametrize(
    "name,content,mime,code",
    [
        ("bad.png", b"not an image", "image/png", "invalid_image"),
        ("empty.jpg", b"", "image/jpeg", "invalid_image"),
        ("picture.svg", b"<svg/>", "image/svg+xml", "unsupported_image"),
    ],
)
def test_rejects_corrupt_empty_and_unsupported(client, project, name, content, mime, code):
    response = client.post(
        f"/api/projects/{project['id']}/images", files={"file": (name, content, mime)}
    )
    assert response.status_code in (400, 415)
    assert response.json()["code"] == code
    assert response.json()["retryable"] is False


def test_accepts_phone_mpo_jpeg_and_keeps_primary_frame():
    stream = io.BytesIO()
    primary = Image.new("RGB", (30, 20), "teal")
    primary.save(stream, "MPO", save_all=True, append_images=[Image.new("RGB", (30, 20), "red")])
    result = sanitize_image(stream.getvalue(), "phone.jpg", "image/jpeg")
    assert result.mime == "image/jpeg"
    with Image.open(io.BytesIO(result.content)) as clean:
        assert clean.format == "JPEG"
        assert getattr(clean, "n_frames", 1) == 1
        assert clean.size == (30, 20)


def test_rejects_disguised_type_and_truncation(image_bytes):
    with pytest.raises(AppError, match="副檔名"):
        sanitize_image(image_bytes, "pretend.jpg", "image/jpeg")
    with pytest.raises(AppError, match="副檔名"):
        sanitize_image(image_bytes, "picture.png", "text/html")
    with pytest.raises(AppError, match="損毀"):
        sanitize_image(image_bytes[:45], "truncated.png", "image/png")
