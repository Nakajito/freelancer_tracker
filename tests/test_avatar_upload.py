"""Avatar uploads are bounded in size, pixels and format.

ImageField only proves Pillow can decode the file. FILE_UPLOAD_MAX_MEMORY_SIZE
is the memory-vs-tempfile threshold, not a cap, so nothing previously stopped a
very large or a decompression-bomb image.
"""

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import avatar_upload_path
from apps.accounts.validators import MAX_AVATAR_BYTES, validate_avatar


def _png(width: int = 16, height: int = 16) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_ordinary_image_passes():
    upload = SimpleUploadedFile("me.png", _png(), content_type="image/png")
    validate_avatar(upload)


def test_oversized_file_is_rejected():
    upload = SimpleUploadedFile("big.png", _png(), content_type="image/png")
    upload.size = MAX_AVATAR_BYTES + 1

    with pytest.raises(ValidationError, match="too large"):
        validate_avatar(upload)


def test_non_image_is_rejected():
    upload = SimpleUploadedFile(
        "payload.png",
        b"<html><script>alert(1)</script></html>",
        content_type="image/png",
    )

    with pytest.raises(ValidationError, match="not a readable image"):
        validate_avatar(upload)


def test_decompression_bomb_dimensions_are_rejected():
    """A tiny file that decodes to an enormous canvas."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None  # let Pillow build it; our validator must object
    buffer = io.BytesIO()
    Image.new("L", (10000, 10000), 0).save(buffer, format="PNG")
    upload = SimpleUploadedFile("bomb.png", buffer.getvalue(), content_type="image/png")

    with pytest.raises(ValidationError, match="dimensions are too large"):
        validate_avatar(upload)


def test_validator_leaves_the_file_readable():
    """Validation must not consume the stream Django is about to save."""
    upload = SimpleUploadedFile("me.png", _png(), content_type="image/png")
    upload.seek(0)

    validate_avatar(upload)

    upload.seek(0)
    assert upload.read(8) == b"\x89PNG\r\n\x1a\n"


def test_stored_path_is_randomized():
    first = avatar_upload_path(None, "../../etc/passwd.png")
    second = avatar_upload_path(None, "../../etc/passwd.png")

    assert first != second
    assert first.startswith("avatars/")
    assert ".." not in first
    assert "passwd" not in first
    assert first.endswith(".png")
