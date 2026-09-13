import os

from flask import Flask

from backend.config import Config
from backend.extensions import db, login_manager
from backend.models import Admin, Vendor


def create_app():
    app = Flask(
        __name__,
        template_folder=Config.TEMPLATE_FOLDER,
        static_folder=Config.STATIC_FOLDER,
        static_url_path="/static",
    )
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Gzip/br-compress every HTML/CSS/JS/JSON response before it goes out --
    # pages with lots of product cards/text shrink a lot over the wire, which
    # matters most for visitors on slower mobile connections. Wrapped in a
    # try/except so the app still runs even if `pip install -r
    # requirements.txt` hasn't been re-run yet after this change.
    try:
        from flask_compress import Compress

        Compress(app)
    except ImportError:
        pass

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # user_id is stored as "admin:<id>" or "vendor:<id>" (see get_id()
        # overrides on the Admin / Vendor models) so one shared session /
        # login manager can serve two completely separate login systems.
        try:
            kind, raw_id = user_id.split(":", 1)
        except ValueError:
            return None

        if kind == "admin":
            return db.session.get(Admin, int(raw_id))
        if kind == "vendor":
            return db.session.get(Vendor, int(raw_id))
        return None

    from backend.controllers.landing_controller import landing_bp
    from backend.controllers.admin_controller import admin_bp
    from backend.controllers.vendor_controller import vendor_bp
    from backend.controllers.public_controller import public_bp

    app.register_blueprint(landing_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(vendor_bp, url_prefix="/vendor")
    app.register_blueprint(public_bp, url_prefix="/store/<string:slug>")

    @app.context_processor
    def inject_platform_settings():
        # Used only by the Admin / Vendor panel templates.
        return {"PLATFORM_NAME": app.config["PLATFORM_NAME"]}

    from backend.utils.helpers import favicon_url, image_url
    app.jinja_env.globals["image_url"] = image_url
    app.jinja_env.globals["favicon_url"] = favicon_url

    from backend.utils.helpers import asset_url
    app.jinja_env.globals["asset_url"] = asset_url

    from backend.utils.translations import translate
    from flask import session as flask_session

    def t(text):
        return translate(text, flask_session.get("lang", "en"))

    app.jinja_env.globals["t"] = t

    @app.errorhandler(413)
    def file_too_large(e):
        from flask import flash, redirect, request

        flash("Those files are too large to upload together. Please try fewer or smaller photos.", "danger")
        return redirect(request.referrer or "/"), 302

    app.wsgi_app = CustomDomainMiddleware(app.wsgi_app, app)

    return app


class CustomDomainMiddleware:
    """If a request's Host header matches a vendor's custom_domain, silently
    rewrite the path to /store/<slug>/... before Flask's router ever sees
    it -- so visitors on their own domain see their store at "/" instead of
    needing the /store/<slug> path. Runs at the WSGI layer (before routing),
    since Flask has already matched the URL rule by the time any
    before_request hook would run.

    PERFORMANCE: this used to run a fresh DB query for the Host header on
    *every single request* -- including every /static/... file (CSS, JS,
    every product photo) -- since only literal "localhost"/"127.0.0.1" were
    skipped. On a real deploy the Host header is never "localhost", so every
    asset on every page load was paying for a round-trip to the (remote)
    database. That's the main thing that was making the site feel slow.

    Fixed by:
      1. Skipping static file requests entirely -- they can never need a
         custom-domain rewrite.
      2. Caching the host -> vendor-slug lookup in memory for a few minutes,
         so a given host only costs one DB query occasionally instead of on
         every request. Custom domains change extremely rarely, so a short
         staleness window here is a non-issue in practice.
    """

    _CACHE_TTL_SECONDS = 300  # re-check a given host at most every 5 minutes

    def __init__(self, wsgi_app, app):
        self.wsgi_app = wsgi_app
        self.app = app
        self._cache = {}  # host -> (slug_or_None, expires_at_monotonic)

    def _resolve_slug(self, host):
        import time

        cached = self._cache.get(host)
        now = time.monotonic()
        if cached is not None and cached[1] > now:
            return cached[0]

        with self.app.app_context():
            from backend.models import Vendor

            vendor = Vendor.query.filter_by(custom_domain=host, is_active=True).first()
            slug = vendor.slug if vendor else None

        self._cache[host] = (slug, now + self._CACHE_TTL_SECONDS)
        return slug

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        host = environ.get("HTTP_HOST", "").split(":")[0].lower()

        # Static files (css/js/uploaded photos/etc) never need a domain
        # rewrite -- skip the lookup entirely so they're never slowed down.
        if host and host not in ("localhost", "127.0.0.1") and not path.startswith("/static/"):
            slug = self._resolve_slug(host)
            if slug:
                environ["PATH_INFO"] = f"/store/{slug}{path}"

        return self.wsgi_app(environ, start_response)
