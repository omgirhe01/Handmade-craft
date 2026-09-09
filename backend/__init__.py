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

    from backend.utils.helpers import image_url
    app.jinja_env.globals["image_url"] = image_url

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
    """

    def __init__(self, wsgi_app, app):
        self.wsgi_app = wsgi_app
        self.app = app

    def __call__(self, environ, start_response):
        host = environ.get("HTTP_HOST", "").split(":")[0].lower()
        # Skip the lookup entirely for the platform's own domain / localhost
        # so every normal request isn't slowed down by a DB query.
        if host and host not in ("localhost", "127.0.0.1"):
            with self.app.app_context():
                from backend.models import Vendor

                vendor = Vendor.query.filter_by(custom_domain=host, is_active=True).first()
                if vendor:
                    path = environ.get("PATH_INFO", "/")
                    environ["PATH_INFO"] = f"/store/{vendor.slug}{path}"

        return self.wsgi_app(environ, start_response)
