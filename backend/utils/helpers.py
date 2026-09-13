import io
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


def _compress_to_bytes(file_storage):
    """Read an uploaded FileStorage, resize it down to a sane max dimension,
    and return compressed JPEG bytes. Falls back to the raw original bytes
    if it isn't a Pillow-readable image, so a bad photo never breaks the
    upload -- it just skips compression.
    """
    raw = file_storage.read()
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img = ImageOps.exif_transpose(img)  # respect phone camera orientation
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            out = io.BytesIO()
            img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return out.getvalue()
    except Exception:
        return raw


def _cloudinary_configured():
    cfg = current_app.config
    return bool(cfg.get("CLOUDINARY_CLOUD_NAME") and cfg.get("CLOUDINARY_API_KEY") and cfg.get("CLOUDINARY_API_SECRET"))


def _upload_to_cloudinary(image_bytes, vendor_slug):
    """Uploads to Cloudinary and returns the permanent https URL, or None if
    the upload fails for any reason (caller falls back to local disk)."""
    try:
        import cloudinary
        import cloudinary.uploader

        cfg = current_app.config
        cloudinary.config(
            cloud_name=cfg["CLOUDINARY_CLOUD_NAME"],
            api_key=cfg["CLOUDINARY_API_KEY"],
            api_secret=cfg["CLOUDINARY_API_SECRET"],
            secure=True,
        )
        result = cloudinary.uploader.upload(
            io.BytesIO(image_bytes),
            folder=f"handmade-craft-decor/{vendor_slug}",
            public_id=uuid.uuid4().hex,
            resource_type="image",
        )
        return result.get("secure_url")
    except Exception:
        return None


def save_vendor_upload(file, vendor_slug):
    """Save an uploaded image for a vendor. The image is always
    resized/compressed first to keep the store fast.

    - If Cloudinary credentials are configured, the image is uploaded there
      and a permanent https:// URL is returned -- this is what makes photos
      survive restarts/redeploys on Render (its local disk is ephemeral).
    - Otherwise, it's saved to the local uploads/ folder as before (fine for
      local development) and '<slug>/<filename>' is returned.

    Use image_url() (registered as a Jinja global) in templates so both
    storage forms render correctly without templates needing to care which
    one is active.
    """
    compressed = _compress_to_bytes(file)

    if _cloudinary_configured():
        url = _upload_to_cloudinary(compressed, vendor_slug)
        if url:
            return url
        # Cloudinary upload failed (bad credentials, network issue, etc.) --
        # fall through to local disk so the upload doesn't just fail outright.

    unique_name = f"{uuid.uuid4().hex}.jpg"
    vendor_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], vendor_slug)
    os.makedirs(vendor_folder, exist_ok=True)
    with open(os.path.join(vendor_folder, unique_name), "wb") as f:
        f.write(compressed)

    return f"{vendor_slug}/{unique_name}"


def image_url(stored_value, external=False):
    """Build the correct <img src> for a value saved by save_vendor_upload,
    regardless of whether it's a full Cloudinary URL or a local relative
    path. Use this in templates instead of manually building
    url_for('static', filename='uploads/' + value).
    Pass external=True for places needing an absolute URL (e.g. og:image) --
    Cloudinary URLs are always absolute already, so this only affects the
    local-disk fallback."""
    from flask import url_for

    if not stored_value:
        return ""
    if stored_value.startswith("http://") or stored_value.startswith("https://"):
        return stored_value
    return url_for("static", filename="uploads/" + stored_value, _external=external)


def favicon_url(stored_value):
    """Like image_url(), but returns a circular-cropped, transparent-background
    version suitable for a browser tab favicon -- so a rectangular vendor
    logo still shows as a clean circle in the tab, matching the platform's
    own circular favicon.

    - Cloudinary-hosted logos: handled entirely by Cloudinary's own on-the-fly
      transformations (crop to a square, round the corners to a full circle,
      output PNG) -- no extra server work, and it's CDN-cached.
    - Local-disk logos (dev fallback): routed through
      public.vendor_favicon, which crops the image the same way with Pillow.
    """
    from flask import url_for

    if not stored_value:
        return ""
    if stored_value.startswith("http://") or stored_value.startswith("https://"):
        marker = "/upload/"
        idx = stored_value.find(marker)
        if idx == -1:
            return stored_value
        insert_at = idx + len(marker)
        transform = "c_fill,g_auto,w_128,h_128,r_max,f_png/"
        return stored_value[:insert_at] + transform + stored_value[insert_at:]
    return url_for("public.vendor_favicon", stored_value=stored_value)
