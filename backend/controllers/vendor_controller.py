from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from backend.extensions import db
from backend.models import Category, ContactMessage, CustomOrder, Order, Product, Vendor
from backend.utils.decorators import vendor_required
from backend.utils.helpers import allowed_file, save_vendor_upload, unique_slug

vendor_bp = Blueprint("vendor", __name__)


def _my_categories():
    return Category.query.filter_by(vendor_id=current_user.id).all()


# ---------------------------------------------------------------- auth ----

@vendor_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and isinstance(current_user, Vendor):
        return redirect(url_for("vendor.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        acc = Vendor.query.filter_by(email=email).first()

        if acc and acc.check_password(password):
            if not acc.is_active:
                flash("Your account has been deactivated. Please contact the admin.", "danger")
                return render_template("vendor/login.html")
            login_user(acc)
            return redirect(url_for("vendor.dashboard"))
        flash("Invalid email or password.", "danger")

    return render_template("vendor/login.html")


@vendor_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("vendor.login"))


# ----------------------------------------------------------- dashboard ----

@vendor_bp.route("/dashboard")
@vendor_required
def dashboard():
    total_products = Product.query.filter_by(vendor_id=current_user.id).count()
    total_orders = (
        Order.query.filter_by(vendor_id=current_user.id).count()
        + CustomOrder.query.filter_by(vendor_id=current_user.id).count()
    )
    pending_orders = (
        Order.query.filter_by(vendor_id=current_user.id, status="Pending").count()
        + CustomOrder.query.filter_by(vendor_id=current_user.id, status="Pending").count()
    )
    completed_orders = (
        Order.query.filter_by(vendor_id=current_user.id, status="Completed").count()
        + CustomOrder.query.filter_by(vendor_id=current_user.id, status="Completed").count()
    )
    recent_orders = (
        Order.query.filter_by(vendor_id=current_user.id)
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )
    store_url = url_for("public.home", slug=current_user.slug, _external=True)

    return render_template(
        "vendor/dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        recent_orders=recent_orders,
        store_url=store_url,
    )


# ---------------------------------------------------------- categories ----

@vendor_bp.route("/categories")
@vendor_required
def categories():
    return render_template("vendor/categories.html", categories=_my_categories())


@vendor_bp.route("/categories/add", methods=["GET", "POST"])
@vendor_required
def add_category():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Please enter a category name.", "danger")
            return render_template("vendor/category_form.html", category=None)

        slug = unique_slug(
            name,
            lambda s: Category.query.filter_by(vendor_id=current_user.id, slug=s).first()
            is not None,
        )
        db.session.add(Category(vendor_id=current_user.id, name=name, slug=slug))
        db.session.commit()
        flash("Category added.", "success")
        return redirect(url_for("vendor.categories"))

    return render_template("vendor/category_form.html", category=None)


@vendor_bp.route("/categories/edit/<int:category_id>", methods=["GET", "POST"])
@vendor_required
def edit_category(category_id):
    category = Category.query.filter_by(id=category_id, vendor_id=current_user.id).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            category.name = name
        db.session.commit()
        flash("Category updated.", "success")
        return redirect(url_for("vendor.categories"))

    return render_template("vendor/category_form.html", category=category)


@vendor_bp.route("/categories/delete/<int:category_id>", methods=["POST"])
@vendor_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, vendor_id=current_user.id).first_or_404()
    if category.products:
        flash("Move or delete products in this category first.", "danger")
        return redirect(url_for("vendor.categories"))
    db.session.delete(category)
    db.session.commit()
    flash("Category deleted.", "info")
    return redirect(url_for("vendor.categories"))


# ------------------------------------------------------------ products ----

@vendor_bp.route("/products")
@vendor_required
def products():
    all_products = (
        Product.query.filter_by(vendor_id=current_user.id)
        .order_by(Product.created_at.desc())
        .all()
    )
    return render_template("vendor/products.html", products=all_products)


@vendor_bp.route("/products/add", methods=["GET", "POST"])
@vendor_required
def add_product():
    categories = _my_categories()
    if not categories:
        flash("Add a category first before adding products.", "warning")
        return redirect(url_for("vendor.add_category"))

    if request.method == "POST":
        image_filename = "placeholder.png"
        file = request.files.get("image")
        if file and file.filename and allowed_file(file.filename):
            image_filename = save_vendor_upload(file, current_user.slug)

        category_id = int(request.form.get("category_id"))
        category = Category.query.filter_by(id=category_id, vendor_id=current_user.id).first()
        if not category:
            flash("Invalid category.", "danger")
            return render_template("vendor/product_form.html", categories=categories, product=None)

        product = Product(
            vendor_id=current_user.id,
            name=request.form.get("name", "").strip(),
            category_id=category_id,
            price=float(request.form.get("price", 0)),
            description=request.form.get("description", "").strip(),
            material=request.form.get("material", "").strip(),
            size=request.form.get("size", "").strip(),
            colours=request.form.get("colours", "").strip(),
            care=request.form.get("care", "").strip(),
            in_stock=request.form.get("in_stock") == "on",
            image_filename=image_filename,
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully.", "success")
        return redirect(url_for("vendor.products"))

    return render_template("vendor/product_form.html", categories=categories, product=None)


@vendor_bp.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
@vendor_required
def edit_product(product_id):
    product = Product.query.filter_by(id=product_id, vendor_id=current_user.id).first_or_404()
    categories = _my_categories()

    if request.method == "POST":
        file = request.files.get("image")
        if file and file.filename and allowed_file(file.filename):
            product.image_filename = save_vendor_upload(file, current_user.slug)

        category_id = int(request.form.get("category_id"))
        category = Category.query.filter_by(id=category_id, vendor_id=current_user.id).first()
        if category:
            product.category_id = category_id

        product.name = request.form.get("name", "").strip()
        product.price = float(request.form.get("price", 0))
        product.description = request.form.get("description", "").strip()
        product.material = request.form.get("material", "").strip()
        product.size = request.form.get("size", "").strip()
        product.colours = request.form.get("colours", "").strip()
        product.care = request.form.get("care", "").strip()
        product.in_stock = request.form.get("in_stock") == "on"

        db.session.commit()
        flash("Product updated successfully.", "success")
        return redirect(url_for("vendor.products"))

    return render_template("vendor/product_form.html", categories=categories, product=product)


@vendor_bp.route("/products/delete/<int:product_id>", methods=["POST"])
@vendor_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id, vendor_id=current_user.id).first_or_404()
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "info")
    return redirect(url_for("vendor.products"))


# -------------------------------------------------------------- orders ----

@vendor_bp.route("/orders")
@vendor_required
def orders():
    all_orders = (
        Order.query.filter_by(vendor_id=current_user.id).order_by(Order.created_at.desc()).all()
    )
    return render_template("vendor/orders.html", orders=all_orders)


@vendor_bp.route("/orders/status/<int:order_id>", methods=["POST"])
@vendor_required
def update_order_status(order_id):
    order = Order.query.filter_by(id=order_id, vendor_id=current_user.id).first_or_404()
    order.status = request.form.get("status", order.status)
    db.session.commit()
    flash("Order status updated.", "success")
    return redirect(url_for("vendor.orders"))


@vendor_bp.route("/custom-orders")
@vendor_required
def custom_orders():
    all_custom = (
        CustomOrder.query.filter_by(vendor_id=current_user.id)
        .order_by(CustomOrder.created_at.desc())
        .all()
    )
    return render_template("vendor/custom_orders.html", custom_orders=all_custom)


@vendor_bp.route("/custom-orders/status/<int:order_id>", methods=["POST"])
@vendor_required
def update_custom_order_status(order_id):
    custom = CustomOrder.query.filter_by(id=order_id, vendor_id=current_user.id).first_or_404()
    custom.status = request.form.get("status", custom.status)
    db.session.commit()
    flash("Custom order status updated.", "success")
    return redirect(url_for("vendor.custom_orders"))


@vendor_bp.route("/messages")
@vendor_required
def messages():
    all_messages = (
        ContactMessage.query.filter_by(vendor_id=current_user.id)
        .order_by(ContactMessage.created_at.desc())
        .all()
    )
    return render_template("vendor/messages.html", messages=all_messages)


# --------------------------------------------------------- site settings ----

@vendor_bp.route("/settings", methods=["GET", "POST"])
@vendor_required
def settings():
    if request.method == "POST":
        current_user.business_name = request.form.get("business_name", "").strip() or current_user.business_name
        current_user.tagline = request.form.get("tagline", "").strip()
        current_user.story = request.form.get("story", "").strip()
        current_user.about_text = request.form.get("about_text", "").strip()
        current_user.phone_number = request.form.get("phone_number", "").strip()
        current_user.whatsapp_number = request.form.get("whatsapp_number", "").strip()
        current_user.contact_email = request.form.get("contact_email", "").strip()
        current_user.address = request.form.get("address", "").strip()
        current_user.instagram_url = request.form.get("instagram_url", "").strip()
        current_user.facebook_url = request.form.get("facebook_url", "").strip()

        logo = request.files.get("logo")
        if logo and logo.filename and allowed_file(logo.filename):
            current_user.logo_filename = save_vendor_upload(logo, current_user.slug)

        cover = request.files.get("cover")
        if cover and cover.filename and allowed_file(cover.filename):
            current_user.cover_filename = save_vendor_upload(cover, current_user.slug)

        new_password = request.form.get("new_password", "")
        if new_password:
            current_user.set_password(new_password)

        db.session.commit()
        flash("Store settings updated.", "success")
        return redirect(url_for("vendor.settings"))

    store_url = url_for("public.home", slug=current_user.slug, _external=True)
    return render_template("vendor/site_settings.html", store_url=store_url)
