import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")

    # ---- MySQL connection (read from .env) ----
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_DB = os.environ.get("MYSQL_DB", "handmade_creations")

    # Set USE_SQLITE=1 in .env to run/demo instantly without installing MySQL.
    USE_SQLITE = os.environ.get("USE_SQLITE", "0") == "1"

    if USE_SQLITE:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "database", "dev.db")
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:"
            f"{MYSQL_PORT}/{MYSQL_DB}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- Frontend paths (templates & static live outside backend/) ----
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, "frontend", "templates")
    STATIC_FOLDER = os.path.join(BASE_DIR, "frontend", "static")

    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # ---- Platform branding (shown only on the Admin / Vendor panels, never
    # on an individual vendor's public storefront) ----
    PLATFORM_NAME = os.environ.get("PLATFORM_NAME", "Handmade Craft Decor")
