from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user

from backend.models import Admin, Vendor

landing_bp = Blueprint("landing", __name__)


@landing_bp.route("/")
def home():
    return render_template("landing.html")


@landing_bp.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, send straight to the right dashboard instead of
    # showing the login form again.
    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for("admin.dashboard"))
        if isinstance(current_user, Vendor):
            return redirect(url_for("vendor.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        # A vendor can log in with either their email or their phone number.
        vendor = Vendor.query.filter(
            (Vendor.email == identifier.lower()) | (Vendor.phone_number == identifier)
        ).first()
        if vendor and vendor.check_password(password):
            if not vendor.is_active:
                flash("Your account has been deactivated. Please contact the admin.", "danger")
                return render_template("login.html")
            login_user(vendor)
            return redirect(url_for("vendor.dashboard"))

        # Otherwise check the platform admin (logs in with username).
        admin = Admin.query.filter_by(username=identifier).first()
        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for("admin.dashboard"))

        flash("Invalid email/phone/username or password.", "danger")

    return render_template("login.html")
