"""Upload validation.

Technical Documentation Section 03 (operating assumptions) and Section 13
(security controls): accepted formats are JPG/JPEG/PNG with a 5 MB ceiling,
and validation checks the decoded image content -- not just the filename
extension -- so a malicious file cannot masquerade as an image.
"""

from io import BytesIO
from PIL import Image, UnidentifiedImageError

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

    return image.convert("RGB")
