"""Server-side validation of uploaded images.

The check is on the file CONTENT (decoded by Pillow), not the filename or the
client-supplied Content-Type, both of which are attacker-controlled.
Nothing is written to disk: the upload lives in memory for the duration of the request.
"""
from django.conf import settings
from PIL import Image, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class UploadRejected(Exception):
    def __init__(self, code, message, http_status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def validate_image_upload(uploaded):
    """Return a decoded PIL image, or raise UploadRejected."""
    if uploaded is None:
        raise UploadRejected("IMAGE_REQUIRED", "No image was uploaded. Send it as multipart/form-data in the 'image' field.")
    if uploaded.size == 0:
        raise UploadRejected("EMPTY_FILE", "The uploaded file is empty.")
    if uploaded.size > settings.PREDICT_MAX_UPLOAD_BYTES:
        mb = settings.PREDICT_MAX_UPLOAD_BYTES / 1024 / 1024
        raise UploadRejected("FILE_TOO_LARGE", f"The image is too large. The maximum size is {mb:g} MB.", 413)

    try:
        uploaded.seek(0)
        probe = Image.open(uploaded)
        fmt = probe.format
        width, height = probe.size
        if fmt not in ALLOWED_FORMATS:
            raise UploadRejected("UNSUPPORTED_IMAGE_TYPE", "Unsupported image type. Please upload a JPG, PNG or WEBP image.", 415)
        if width * height > settings.PREDICT_MAX_IMAGE_PIXELS:
            raise UploadRejected("IMAGE_DIMENSIONS_TOO_LARGE", "The image dimensions are too large.", 413)
        probe.verify()  # structural integrity check (invalidates `probe`)
        uploaded.seek(0)
        image = Image.open(uploaded)
        image.load()  # full decode: catches truncated / corrupt data
    except UploadRejected:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, SyntaxError, OSError, ValueError):
        raise UploadRejected("INVALID_IMAGE", "The file is not a valid image.")
    return image
