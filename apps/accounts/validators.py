"""Upload validation for user-supplied images.

Django's ``ImageField`` only proves Pillow can decode the file. It does not
bound the size (``FILE_UPLOAD_MAX_MEMORY_SIZE`` is the memory-vs-tempfile
threshold, not a limit, so oversized uploads simply spool to disk), and it does
not bound the decoded pixel count, so a small highly-compressed image can
expand to gigabytes of RAM when Pillow opens it.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_AVATAR_PIXELS = 8000 * 8000  # generous, but bounded
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


def validate_avatar(uploaded: Any) -> None:
    """Reject oversized, over-large or non-image uploads."""
    size = getattr(uploaded, "size", None)
    if size is not None and size > MAX_AVATAR_BYTES:
        raise ValidationError(
            _("Image is too large (maximum %(mb)s MB).")
            % {"mb": MAX_AVATAR_BYTES // (1024 * 1024)}
        )

    from PIL import Image

    position = uploaded.tell() if hasattr(uploaded, "tell") else None
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as image:
            image_format = (image.format or "").upper()
            width, height = image.size
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(_("That file is not a readable image.")) from exc
    finally:
        if position is not None:
            uploaded.seek(position)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            _("Unsupported image format. Use JPEG, PNG, WebP or GIF.")
        )

    if width * height > MAX_AVATAR_PIXELS:
        # Decompression bomb: cheap to send, expensive to decode.
        raise ValidationError(_("Image dimensions are too large."))
