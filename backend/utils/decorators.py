from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user

from backend.models import Admin, Vendor


def admin_required(f):
    """Only lets a logged-in Admin (super admin / platform owner) through."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Admin):
            flash("Please log in to access the admin dashboard.", "warning")
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)

    return wrapped


def vendor_required(f):
    """Only lets a logged-in Vendor (business-owner user) through."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Vendor):
            flash("Please log in to access your dashboard.", "warning")
            return redirect(url_for("vendor.login"))
        return f(*args, **kwargs)

    return wrapped
