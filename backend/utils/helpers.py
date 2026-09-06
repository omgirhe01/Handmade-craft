import os
import re
import uuid

from flask import current_app
from werkzeug.utils import secure_filename


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


def save_vendor_upload(file, vendor_slug):
    """Save an uploaded image inside a per-vendor sub-folder of the uploads
    directory so files from different vendors never collide or mix.
    Returns the stored value to keep on the model, e.g. '<slug>/<filename>'.
    """
    original = secure_filename(file.filename)
    ext = original.rsplit(".", 1)[1].lower() if "." in original else "jpg"
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    vendor_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], vendor_slug)
    os.makedirs(vendor_folder, exist_ok=True)
    file.save(os.path.join(vendor_folder, unique_name))

    return f"{vendor_slug}/{unique_name}"
