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

    @app.errorhandler(413)
    def file_too_large(e):
        from flask import flash, redirect, request

        flash("Those files are too large to upload together. Please try fewer or smaller photos.", "danger")
        return redirect(request.referrer or "/"), 302

    return app
