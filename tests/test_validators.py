"""Unit tests: upload validation (Chapter 4.10.3, IDs prefixed VAL-)."""

import io
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.classifier.validators import validate_upload, UploadValidationError


def _jpeg_file(name="photo.jpg", size=(300, 300), color=(120, 160, 90)):
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="JPEG")
    buf.seek(0)
    return FileStorage(stream=buf, filename=name, content_type="image/jpeg")


def test_val01_valid_jpeg_is_accepted():
    result = validate_upload(_jpeg_file())
    assert result.size == (300, 300)


def test_val02_missing_file_rejected():
    try:
        validate_upload(None)
        assert False, "expected UploadValidationError"
    except UploadValidationError as exc:
        assert exc.code == "no_file"


def test_val03_disallowed_extension_rejected():
    buf = io.BytesIO(b"not really a gif but wrong extension")
    fs = FileStorage(stream=buf, filename="photo.gif", content_type="image/gif")
    try:
        validate_upload(fs)
        assert False, "expected UploadValidationError"
    except UploadValidationError as exc:
        assert exc.code == "unsupported_extension"


def test_val04_oversized_file_rejected():
    buf = io.BytesIO(b"0" * (5 * 1024 * 1024 + 1))
    fs = FileStorage(stream=buf, filename="huge.jpg", content_type="image/jpeg")
    try:
        validate_upload(fs)
        assert False, "expected UploadValidationError"
    except UploadValidationError as exc:
        assert exc.code == "file_too_large"


def test_val05_corrupt_payload_with_jpg_extension_rejected():
    buf = io.BytesIO(b"this is not an image file at all")
    fs = FileStorage(stream=buf, filename="fake.jpg", content_type="image/jpeg")
    try:
        validate_upload(fs)
        assert False, "expected UploadValidationError"
    except UploadValidationError as exc:
        assert exc.code == "corrupt_or_not_an_image"


def test_val06_png_is_accepted():
    buf = io.BytesIO()
    Image.new("RGB", (200, 200), color=(10, 10, 200)).save(buf, format="PNG")
    buf.seek(0)
    fs = FileStorage(stream=buf, filename="photo.png", content_type="image/png")
    result = validate_upload(fs)
    assert result.mode == "RGB"
