"""Upload validation.

Technical Documentation Section 03 (operating assumptions) and Section 13
(security controls): accepted formats are JPG/JPEG/PNG with a 5 MB ceiling,
and validation checks the decoded image content -- not just the filename
extension -- so a malicious file cannot masquerade as an image.
"""

from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_PIL_FORMATS = {"JPEG", "PNG"}
MAX_BYTES = 5 * 1024 * 1024


class UploadValidationError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _extension_of(filename):
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def validate_upload(file_storage):
    """Validate a Werkzeug FileStorage upload.

    Returns a decoded, RGB-converted PIL.Image on success. Raises
    UploadValidationError with a stable machine-readable `code` on
    failure so the API layer can map it to the right response.
    """
    if file_storage is None or file_storage.filename == "":
        raise UploadValidationError("no_file", "No file was submitted.")

    extension = _extension_of(file_storage.filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            "unsupported_extension",
            "Only JPG, JPEG and PNG files are accepted.",
        )

    raw_bytes = file_storage.read()
    file_storage.seek(0)

    if len(raw_bytes) == 0:
        raise UploadValidationError("empty_file", "The uploaded file is empty.")
    if len(raw_bytes) > MAX_BYTES:
        raise UploadValidationError(
            "file_too_large",
            "The uploaded file exceeds the 5 MB limit.",
        )

    try:
        image = Image.open(BytesIO(raw_bytes))
        image.verify()  # confirms the payload really is image data
        # Re-open after verify(); verify() leaves the file object unusable.
        image = Image.open(BytesIO(raw_bytes))
        image_format = image.format
    except (UnidentifiedImageError, OSError):
        raise UploadValidationError(
            "corrupt_or_not_an_image",
            "The uploaded file could not be read as an image.",
        )

    if image_format not in ALLOWED_PIL_FORMATS:
        raise UploadValidationError(
            "unsupported_extension",
            "Only JPG, JPEG and PNG files are accepted.",
        )

    image = image.convert("RGB")

    # Bug fix (2026-09-14): phone cameras write an EXIF orientation tag
    # instead of physically rotating the pixel data (e.g. a photo taken in
    # portrait mode is stored as landscape pixels + "rotate 90" metadata).
    # PIL's Image.open() ignores that tag, so without this correction a
    # phone photo gets resized and fed to the model sideways/upside-down --
    # nothing like the upright, tag-free TrashNet training images (verified
    # directly: none of tests/fixtures/*.jpg carry an orientation tag, so
    # this path was never exercised by the existing test suite). This is
    # the most likely reason classification looked broken specifically for
    # photos taken with a phone. exif_transpose() is a no-op for images
    # that carry no orientation tag (e.g. the existing test fixtures), so
    # it cannot change any already-passing behaviour.
    image = ImageOps.exif_transpose(image)

    return image
