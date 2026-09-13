import os
import ssl as ssl_lib

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")

    # ---- MySQL connection (read from .env) ----
    # Defaults here match a fresh Aiven "defaultdb" MySQL service (Aiven
    # doesn't use the standard port 3306 -- always double-check the actual
    # port/host/db shown on your Aiven service's "Connection information"
    # panel and put those exact values in .env / your host's env vars).
    MYSQL_USER = os.environ.get("MYSQL_USER", "avnadmin")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_DB = os.environ.get("MYSQL_DB", "defaultdb")
    # Aiven (and most managed MySQL hosts) require an SSL connection. Set
    # MYSQL_SSL=0 in .env only for a plain local MySQL install that has no
    # SSL configured (e.g. XAMPP/MySQL on your own PC).
    MYSQL_SSL = os.environ.get("MYSQL_SSL", "1") == "1"

    # Set USE_SQLITE=1 in .env to run/demo instantly without installing MySQL.
    # NOTE: never use USE_SQLITE=1 on Render (or any host with an ephemeral
    # disk) -- the SQLite file gets wiped on every restart/redeploy, so all
    # vendors/products/orders would vanish. Use real MySQL there instead.
    USE_SQLITE = os.environ.get("USE_SQLITE", "0") == "1"

    if USE_SQLITE:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "database", "dev.db")
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:"
            f"{MYSQL_PORT}/{MYSQL_DB}"
        )
        if MYSQL_SSL:
            # Enables TLS (required by Aiven) without needing to download
            # and wire up their CA certificate file.
            _ssl_context = ssl_lib.create_default_context()
            _ssl_context.check_hostname = False
            _ssl_context.verify_mode = ssl_lib.CERT_NONE
            SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"ssl": {"context": _ssl_context}}}
        else:
            SQLALCHEMY_ENGINE_OPTIONS = {}

        # ---- Connection pool tuning ----
        # Without this, SQLAlchemy's default pool can hand out a connection
        # that the managed DB host (Aiven) has silently closed for being
        # idle too long -- the app then has to fail once and reconnect,
        # which shows up as a slow/hanging request. pool_pre_ping does a
        # cheap "is this connection still alive" check before reusing one,
        # and pool_recycle proactively retires connections before Aiven's
        # own idle timeout hits, so requests don't pay for that failure.
        SQLALCHEMY_ENGINE_OPTIONS.update({
            "pool_pre_ping": True,
            "pool_recycle": 280,
            "pool_size": 5,
            "max_overflow": 10,
        })

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- Frontend paths (templates & static live outside backend/) ----
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, "frontend", "templates")
    STATIC_FOLDER = os.path.join(BASE_DIR, "frontend", "static")

    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, "uploads")

    # ---- Static file browser caching ----
    # Product photos are saved under a random uuid filename and never
    # overwritten in place (see save_vendor_upload), and CSS/JS rarely
    # change day-to-day, so it's safe to tell browsers to keep them cached
    # for a week instead of re-requesting every single asset on every page
    # visit. This alone noticeably speeds up repeat visits.
    SEND_FILE_MAX_AGE_DEFAULT = 7 * 24 * 60 * 60  # 7 days, in seconds
    # Raw photos (before our automatic compression) can be several MB each,
    # especially phone camera photos, and a product can have several gallery
    # photos uploaded in the same request -- so this needs real headroom.
    MAX_CONTENT_LENGTH = 30 * 1024 * 1024  # 30 MB per request
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # ---- Persistent image storage (Cloudinary) ----
    # Render's (and most PaaS) local disk is EPHEMERAL: anything saved to
    # UPLOAD_FOLDER disappears on the next restart/redeploy, which is why
    # uploaded photos were vanishing. When these three variables are set,
    # save_vendor_upload() uploads to Cloudinary instead and photos persist
    # forever, independent of the app's disk. If they're not set (e.g. in
    # local development), uploads fall back to the local disk as before.
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

    # ---- Platform branding (shown only on the Admin / Vendor panels, never
    # on an individual vendor's public storefront) ----
    PLATFORM_NAME = os.environ.get("PLATFORM_NAME", "Handmade Craft Decor")
