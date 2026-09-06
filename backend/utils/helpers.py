import os
import re
import uuid

from flask import current_app
from PIL import Image, ImageOps

MAX_DIMENSION = 1600  # px, longest side
JPEG_QUALITY = 78


def allowed_file(filename):
    """Check whether the uploaded file has an allowed image extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


def slugify(text):
    """Turn 'Priya's Craft Studio' into 'priyas-craft-studio'."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "store"


def unique_slug(base_text, exists_fn):
    """Generate a slug from base_text, appending -2, -3, ... until exists_fn(slug)
    returns False. exists_fn should be a callable that takes a slug and returns
    True if it's already taken."""
    base = slugify(base_text)
    slug = base
    counter = 2
    while exists_fn(slug):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _compress_image(src_path):
    """Resize large photos down to a sane max dimension and re-save with
    compression, so a vendor uploading a 6000x4000 phone photo doesn't slow
    down every visitor's page load. Runs in place; falls back silently to
    the original file if it isn't a Pillow-readable image (e.g. corrupt
    upload) so a bad photo never breaks the save.
    """
    try:
        with Image.open(src_path) as img:
            img = ImageOps.exif_transpose(img)  # respect phone camera orientation
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.save(src_path, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    except Exception:
        # Not a valid/openable image (or Pillow doesn't support it) -- leave
        # the originally-saved file untouched rather than failing the upload.
        pass


def save_vendor_upload(file, vendor_slug):
    """Save an uploaded image inside a per-vendor sub-folder of the uploads
    directory so files from different vendors never collide or mix. The
    image is automatically resized/compressed to keep the store fast.
    Returns the stored value to keep on the model, e.g. '<slug>/<filename>'.
    """
    # Photos are always re-saved as JPEG during compression, so the stored
    # filename uses a .jpg extension regardless of the original upload type.
    unique_name = f"{uuid.uuid4().hex}.jpg"

    vendor_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], vendor_slug)
    os.makedirs(vendor_folder, exist_ok=True)
    dest_path = os.path.join(vendor_folder, unique_name)
    file.save(dest_path)
    _compress_image(dest_path)

    return f"{vendor_slug}/{unique_name}"
