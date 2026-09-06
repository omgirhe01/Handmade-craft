from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from backend.extensions import db
from backend.models import Admin, ContactMessage, CustomOrder, Order, Product, Vendor, VendorNotification
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


@admin_bp.route("/analytics")
@admin_required
def analytics():
    from collections import defaultdict
    from datetime import timedelta

    all_orders = Order.query.all()
    total_revenue = sum(float(o.total_price) for o in all_orders)

    # Revenue for each of the last 7 days across the whole platform
    today = datetime.utcnow().date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    revenue_by_day = defaultdict(float)
    for o in all_orders:
        revenue_by_day[o.created_at.date()] += float(o.total_price)
    daily_revenue = [(d.strftime("%d %b"), revenue_by_day.get(d, 0)) for d in last_7_days]
    max_daily = max([r for _, r in daily_revenue] + [1])

    # Top vendors by revenue
    revenue_by_vendor = defaultdict(float)
    orders_by_vendor = defaultdict(int)
    for o in all_orders:
        revenue_by_vendor[o.vendor_id] += float(o.total_price)
        orders_by_vendor[o.vendor_id] += 1
    top_vendor_ids = sorted(revenue_by_vendor, key=lambda vid: revenue_by_vendor[vid], reverse=True)[:5]
    top_vendors = [
        {
            "vendor": db.session.get(Vendor, vid),
            "revenue": revenue_by_vendor[vid],
            "orders": orders_by_vendor[vid],
        }
        for vid in top_vendor_ids
    ]

    # Vendor signups over the last 7 days
    all_vendors = Vendor.query.all()
    signups_by_day = defaultdict(int)
    for v in all_vendors:
        signups_by_day[v.created_at.date()] += 1
    daily_signups = [(d.strftime("%d %b"), signups_by_day.get(d, 0)) for d in last_7_days]
    max_signups = max([s for _, s in daily_signups] + [1])

    return render_template(
        "admin/analytics.html",
        total_revenue=total_revenue,
        total_orders=len(all_orders),
        total_vendors=len(all_vendors),
        daily_revenue=daily_revenue,
        max_daily=max_daily,
        top_vendors=top_vendors,
        daily_signups=daily_signups,
        max_signups=max_signups,
    )


@admin_bp.route("/vendors/<int:vendor_id>/notify", methods=["POST"])
@admin_required
def notify_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    message = request.form.get("message", "").strip()
    if not message:
        flash("Please enter a message to send.", "danger")
        return redirect(url_for("admin.edit_vendor", vendor_id=vendor.id))

    db.session.add(VendorNotification(vendor_id=vendor.id, message=message))
    db.session.commit()
    flash(f"Notification sent to '{vendor.business_name}'.", "success")
    return redirect(url_for("admin.edit_vendor", vendor_id=vendor.id))
