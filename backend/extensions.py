from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
# Admin and Vendor each have their own login page + their own custom
# @admin_required / @vendor_required decorators (see backend/utils/decorators.py),
# so Flask-Login's generic login_view is only a fallback and should rarely trigger.
login_manager.login_view = "landing.home"
