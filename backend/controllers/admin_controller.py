from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from backend.extensions import db
from backend.models import Admin, ContactMessage, CustomOrder, Order, Product, Vendor
from backend.utils.decorators import admin_required
from backend.utils.helpers import unique_slug

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and isinstance(current_user, Admin):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for("admin.dashboard"))
        flash("Invalid username or password.", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    total_vendors = Vendor.query.count()
    active_vendors = Vendor.query.filter_by(is_active=True).count()
    total_products = Product.query.count()
    total_orders = Order.query.count() + CustomOrder.query.count()
    total_messages = ContactMessage.query.count()
    recent_vendors = Vendor.query.order_by(Vendor.created_at.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        total_vendors=total_vendors,
        active_vendors=active_vendors,
        total_products=total_products,
        total_orders=total_orders,
        total_messages=total_messages,
        recent_vendors=recent_vendors,
    )


@admin_bp.route("/vendors")
@admin_required
def vendors():
    all_vendors = Vendor.query.order_by(Vendor.created_at.desc()).all()
    return render_template("admin/vendors.html", vendors=all_vendors)


@admin_bp.route("/vendors/add", methods=["GET", "POST"])
@admin_required
def add_vendor():
    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")
        custom_slug = request.form.get("slug", "").strip()

        if not business_name or not owner_name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("admin/vendor_form.html", vendor=None, form=request.form)

        if Vendor.query.filter_by(email=email).first():
            flash("A vendor with this email already exists.", "danger")
            return render_template("admin/vendor_form.html", vendor=None, form=request.form)

        base_for_slug = custom_slug or business_name
        slug = unique_slug(
            base_for_slug, lambda s: Vendor.query.filter_by(slug=s).first() is not None
        )

        vendor = Vendor(
            business_name=business_name,
            owner_name=owner_name,
            email=email,
            phone_number=phone_number,
            whatsapp_number=phone_number,
            slug=slug,
        )
        vendor.set_password(password)
        db.session.add(vendor)
        db.session.commit()
        flash(f"Vendor '{business_name}' created. Store link: /store/{slug}", "success")
        return redirect(url_for("admin.vendors"))

    return render_template("admin/vendor_form.html", vendor=None, form=None)


@admin_bp.route("/vendors/edit/<int:vendor_id>", methods=["GET", "POST"])
@admin_required
def edit_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)

    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")

        existing = Vendor.query.filter_by(email=email).first()
        if existing and existing.id != vendor.id:
            flash("Another vendor already uses this email.", "danger")
            return render_template("admin/vendor_form.html", vendor=vendor, form=None)

        vendor.business_name = business_name or vendor.business_name
        vendor.owner_name = owner_name or vendor.owner_name
        vendor.email = email or vendor.email
        vendor.phone_number = phone_number
        if password:
            vendor.set_password(password)

        db.session.commit()
        flash("Vendor updated successfully.", "success")
        return redirect(url_for("admin.vendors"))

    return render_template("admin/vendor_form.html", vendor=vendor, form=None)


@admin_bp.route("/vendors/toggle/<int:vendor_id>", methods=["POST"])
@admin_required
def toggle_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    vendor.is_active = not vendor.is_active
    db.session.commit()
    state = "activated" if vendor.is_active else "deactivated"
    flash(f"Vendor '{vendor.business_name}' {state}.", "info")
    return redirect(url_for("admin.vendors"))


@admin_bp.route("/vendors/delete/<int:vendor_id>", methods=["POST"])
@admin_required
def delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    db.session.delete(vendor)
    db.session.commit()
    flash("Vendor and all their store data have been deleted.", "info")
    return redirect(url_for("admin.vendors"))
