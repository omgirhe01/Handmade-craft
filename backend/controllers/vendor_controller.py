import csv
import io
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user

from backend.extensions import db
from backend.models import (
    Category,
    ContactMessage,
    Coupon,
    CustomOrder,
    Order,
    Product,
    ProductImage,
    ProductVariant,
    Review,
    Testimonial,
    Vendor,
    VendorNotification,
)
from backend.utils.decorators import vendor_required
from backend.utils.helpers import allowed_file, save_vendor_upload, unique_slug
from backend.utils.invoice import generate_custom_order_invoice_pdf, generate_order_invoice_pdf
from sqlalchemy.orm import joinedload

vendor_bp = Blueprint("vendor", __name__)


def _my_categories():
    return Category.query.filter_by(vendor_id=current_user.id).all()


# ---------------------------------------------------------------- auth ----

@vendor_bp.route("/login", methods=["GET", "POST"])
def login():
    # Admin and Vendor now share one login page.
    return redirect(url_for("landing.login"))


@vendor_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing.login"))


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
        Order.query.options(joinedload(Order.product))
        .filter_by(vendor_id=current_user.id)
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )
    low_stock_products = [
        p for p in Product.query.filter_by(vendor_id=current_user.id, in_stock=True).all()
        if p.is_low_stock
    ]
    store_url = url_for("public.home", slug=current_user.slug, _external=True)

    total_categories = Category.query.filter_by(vendor_id=current_user.id).count()
    onboarding_steps = [
        {"label": "Add at least one category", "done": total_categories > 0, "link": url_for("vendor.categories")},
        {"label": "Add your first product", "done": total_products > 0, "link": url_for("vendor.products")},
        {"label": "Add your logo and cover photo", "done": bool(current_user.logo_filename or current_user.cover_filename), "link": url_for("vendor.settings")},
        {"label": "Write your story / about text", "done": bool(current_user.story or current_user.about_text), "link": url_for("vendor.settings")},
        {"label": "Add your contact number", "done": bool(current_user.phone_number or current_user.whatsapp_number), "link": url_for("vendor.settings")},
        {"label": "Share your store link", "done": total_orders > 0, "link": None},
    ]
    onboarding_complete = all(s["done"] for s in onboarding_steps)

    return render_template(
        "vendor/dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products,
        store_url=store_url,
        onboarding_steps=onboarding_steps,
        onboarding_complete=onboarding_complete,
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
        Product.query.options(joinedload(Product.category))
        .filter_by(vendor_id=current_user.id)
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
            is_featured=request.form.get("is_featured") == "on",
            stock_quantity=int(request.form.get("stock_quantity") or 10),
            image_filename=image_filename,
        )
        db.session.add(product)
        db.session.commit()

        gallery_files = request.files.getlist("gallery_images")
        for pos, gfile in enumerate(gallery_files):
            if gfile and gfile.filename and allowed_file(gfile.filename):
                gname = save_vendor_upload(gfile, current_user.slug)
                db.session.add(ProductImage(product_id=product.id, image_filename=gname, position=pos))
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
        product.is_featured = request.form.get("is_featured") == "on"
        product.stock_quantity = int(request.form.get("stock_quantity") or 0)

        db.session.commit()

        gallery_files = request.files.getlist("gallery_images")
        existing_count = len(product.gallery_images)
        for pos, gfile in enumerate(gallery_files):
            if gfile and gfile.filename and allowed_file(gfile.filename):
                gname = save_vendor_upload(gfile, current_user.slug)
                db.session.add(
                    ProductImage(
                        product_id=product.id, image_filename=gname, position=existing_count + pos
                    )
                )
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


@vendor_bp.route("/products/<int:product_id>/gallery/delete/<int:image_id>", methods=["POST"])
@vendor_required
def delete_gallery_image(product_id, image_id):
    product = Product.query.filter_by(id=product_id, vendor_id=current_user.id).first_or_404()
    image = ProductImage.query.filter_by(id=image_id, product_id=product.id).first_or_404()
    db.session.delete(image)
    db.session.commit()
    flash("Photo removed.", "info")
    return redirect(url_for("vendor.edit_product", product_id=product.id))


@vendor_bp.route("/products/<int:product_id>/variants/add", methods=["POST"])
@vendor_required
def add_variant(product_id):
    product = Product.query.filter_by(id=product_id, vendor_id=current_user.id).first_or_404()
    label = request.form.get("variant_label", "").strip()
    price = request.form.get("variant_price", "").strip()
    stock = request.form.get("variant_stock", "10").strip()

    if not label or not price:
        flash("Please enter both a label and price for the option.", "danger")
        return redirect(url_for("vendor.edit_product", product_id=product.id))

    try:
        price_val = float(price)
        stock_val = int(stock or 10)
    except ValueError:
        flash("Price and stock must be numbers.", "danger")
        return redirect(url_for("vendor.edit_product", product_id=product.id))

    position = len(product.variants)
    db.session.add(
        ProductVariant(product_id=product.id, label=label, price=price_val, stock_quantity=stock_val, position=position)
    )
    db.session.commit()
    flash("Option added.", "success")
    return redirect(url_for("vendor.edit_product", product_id=product.id))


@vendor_bp.route("/products/<int:product_id>/variants/delete/<int:variant_id>", methods=["POST"])
@vendor_required
def delete_variant(product_id, variant_id):
    product = Product.query.filter_by(id=product_id, vendor_id=current_user.id).first_or_404()
    variant = ProductVariant.query.filter_by(id=variant_id, product_id=product.id).first_or_404()
    db.session.delete(variant)
    db.session.commit()
    flash("Option removed.", "info")
    return redirect(url_for("vendor.edit_product", product_id=product.id))


@vendor_bp.route("/products/bulk-upload", methods=["GET", "POST"])
@vendor_required
def bulk_upload_products():
    categories = _my_categories()

    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or not file.filename:
            flash("Please choose a CSV file to upload.", "danger")
            return render_template("vendor/bulk_upload.html", categories=categories)

        if not file.filename.lower().endswith(".csv"):
            flash("Please upload a .csv file.", "danger")
            return render_template("vendor/bulk_upload.html", categories=categories)

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
            reader = csv.DictReader(stream)
        except Exception:
            flash("Could not read that CSV file. Please check the format.", "danger")
            return render_template("vendor/bulk_upload.html", categories=categories)

        category_by_name = {c.name.strip().lower(): c for c in categories}
        added, skipped = 0, 0

        for row in reader:
            name = (row.get("name") or "").strip()
            category_name = (row.get("category") or "").strip()
            price_raw = (row.get("price") or "").strip()

            if not name or not category_name or not price_raw:
                skipped += 1
                continue

            category = category_by_name.get(category_name.lower())
            if not category:
                # Auto-create the category if it doesn't exist yet.
                slug = unique_slug(
                    category_name,
                    lambda s: Category.query.filter_by(vendor_id=current_user.id, slug=s).first()
                    is not None,
                )
                category = Category(vendor_id=current_user.id, name=category_name, slug=slug)
                db.session.add(category)
                db.session.flush()
                category_by_name[category_name.lower()] = category

            try:
                price = float(price_raw)
            except ValueError:
                skipped += 1
                continue

            db.session.add(
                Product(
                    vendor_id=current_user.id,
                    name=name,
                    category_id=category.id,
                    price=price,
                    description=(row.get("description") or "").strip(),
                    material=(row.get("material") or "").strip() or "Premium Quality Wool",
                    size=(row.get("size") or "").strip(),
                    colours=(row.get("colours") or "").strip(),
                    care=(row.get("care") or "").strip() or "Dry Clean Only",
                    in_stock=(row.get("in_stock") or "yes").strip().lower() not in ("no", "0", "false"),
                    stock_quantity=int(row.get("stock_quantity") or 10),
                )
            )
            added += 1

        db.session.commit()
        flash(f"Bulk upload complete: {added} product(s) added, {skipped} row(s) skipped.", "success")
        return redirect(url_for("vendor.products"))

    return render_template("vendor/bulk_upload.html", categories=categories)


# -------------------------------------------------------------- orders ----

@vendor_bp.route("/orders")
@vendor_required
def orders():
    all_orders = (
        Order.query.options(joinedload(Order.product))
        .filter_by(vendor_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
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
        current_user.theme_color = request.form.get("theme_color", "").strip() or current_user.theme_color
        current_user.announcement_text = request.form.get("announcement_text", "").strip()
        current_user.meta_description = request.form.get("meta_description", "").strip()
        current_user.is_maintenance = request.form.get("is_maintenance") == "on"

        try:
            current_user.delivery_charge = float(request.form.get("delivery_charge") or 0)
        except ValueError:
            current_user.delivery_charge = 0

        custom_domain = request.form.get("custom_domain", "").strip().lower()
        custom_domain = custom_domain.replace("https://", "").replace("http://", "").rstrip("/")
        if custom_domain:
            existing = Vendor.query.filter_by(custom_domain=custom_domain).first()
            if existing and existing.id != current_user.id:
                flash("That custom domain is already connected to another store.", "danger")
                return redirect(url_for("vendor.settings"))
            current_user.custom_domain = custom_domain
        else:
            current_user.custom_domain = None

        logo = request.files.get("logo")
        if logo and logo.filename and allowed_file(logo.filename):
            current_user.logo_filename = save_vendor_upload(logo, current_user.slug)

        cover = request.files.get("cover")
        if cover and cover.filename and allowed_file(cover.filename):
            current_user.cover_filename = save_vendor_upload(cover, current_user.slug)

        story_image = request.files.get("story_image")
        if story_image and story_image.filename and allowed_file(story_image.filename):
            current_user.story_image_filename = save_vendor_upload(story_image, current_user.slug)

        upi_qr = request.files.get("upi_qr")
        if upi_qr and upi_qr.filename and allowed_file(upi_qr.filename):
            current_user.upi_qr_filename = save_vendor_upload(upi_qr, current_user.slug)

        new_password = request.form.get("new_password", "")
        if new_password:
            current_user.set_password(new_password)

        db.session.commit()
        flash("Store settings updated.", "success")
        return redirect(url_for("vendor.settings"))

    store_url = url_for("public.home", slug=current_user.slug, _external=True)
    return render_template("vendor/site_settings.html", store_url=store_url)


@vendor_bp.route("/store-qr.png")
@vendor_required
def store_qr_code():
    import io

    import qrcode

    store_url = url_for("public.home", slug=current_user.slug, _external=True)
    img = qrcode.make(store_url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(
        buf, mimetype="image/png", as_attachment=True,
        download_name=f"{current_user.slug}-store-qr.png",
    )


# ----------------------------------------------------------- testimonials ----

@vendor_bp.route("/testimonials")
@vendor_required
def testimonials():
    all_testimonials = (
        Testimonial.query.filter_by(vendor_id=current_user.id)
        .order_by(Testimonial.created_at.desc())
        .all()
    )
    return render_template("vendor/testimonials.html", testimonials=all_testimonials)


@vendor_bp.route("/testimonials/add", methods=["GET", "POST"])
@vendor_required
def add_testimonial():
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        message = request.form.get("message", "").strip()
        if not customer_name or not message:
            flash("Please fill in the customer name and message.", "danger")
            return render_template("vendor/testimonial_form.html", testimonial=None)

        rating = max(1, min(5, int(request.form.get("rating") or 5)))
        db.session.add(
            Testimonial(
                vendor_id=current_user.id,
                customer_name=customer_name,
                message=message,
                rating=rating,
            )
        )
        db.session.commit()
        flash("Testimonial added.", "success")
        return redirect(url_for("vendor.testimonials"))

    return render_template("vendor/testimonial_form.html", testimonial=None)


@vendor_bp.route("/testimonials/edit/<int:testimonial_id>", methods=["GET", "POST"])
@vendor_required
def edit_testimonial(testimonial_id):
    testimonial = Testimonial.query.filter_by(
        id=testimonial_id, vendor_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        testimonial.customer_name = request.form.get("customer_name", "").strip()
        testimonial.message = request.form.get("message", "").strip()
        testimonial.rating = max(1, min(5, int(request.form.get("rating") or 5)))
        db.session.commit()
        flash("Testimonial updated.", "success")
        return redirect(url_for("vendor.testimonials"))

    return render_template("vendor/testimonial_form.html", testimonial=testimonial)


@vendor_bp.route("/testimonials/delete/<int:testimonial_id>", methods=["POST"])
@vendor_required
def delete_testimonial(testimonial_id):
    testimonial = Testimonial.query.filter_by(
        id=testimonial_id, vendor_id=current_user.id
    ).first_or_404()
    db.session.delete(testimonial)
    db.session.commit()
    flash("Testimonial deleted.", "info")
    return redirect(url_for("vendor.testimonials"))


@vendor_bp.route("/analytics")
@vendor_required
def analytics():
    from collections import defaultdict
    from datetime import timedelta
    from sqlalchemy import func

    all_orders = Order.query.filter_by(vendor_id=current_user.id).all()

    total_revenue = sum(float(o.total_price) for o in all_orders)
    completed_revenue = sum(float(o.total_price) for o in all_orders if o.status == "Completed")

    # Revenue for each of the last 7 days
    today = datetime.utcnow().date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    revenue_by_day = defaultdict(float)
    for o in all_orders:
        revenue_by_day[o.created_at.date()] += float(o.total_price)
    daily_revenue = [(d.strftime("%d %b"), revenue_by_day.get(d, 0)) for d in last_7_days]
    max_daily = max([r for _, r in daily_revenue] + [1])

    # Top-selling products by units ordered
    units_by_product = defaultdict(int)
    revenue_by_product = defaultdict(float)
    for o in all_orders:
        units_by_product[o.product_id] += o.quantity
        revenue_by_product[o.product_id] += float(o.total_price)
    top_product_ids = sorted(units_by_product, key=lambda pid: units_by_product[pid], reverse=True)[:5]
    top_products = [
        {
            "product": db.session.get(Product, pid),
            "units": units_by_product[pid],
            "revenue": revenue_by_product[pid],
        }
        for pid in top_product_ids
    ]

    # Best-performing category by revenue
    revenue_by_category = defaultdict(float)
    for o in all_orders:
        cat_name = o.product.category.name if o.product and o.product.category else "Uncategorised"
        revenue_by_category[cat_name] += float(o.total_price)
    top_categories = sorted(revenue_by_category.items(), key=lambda kv: kv[1], reverse=True)[:5]
    max_cat_revenue = max([v for _, v in top_categories] + [1])

    status_counts = defaultdict(int)
    for o in all_orders:
        status_counts[o.status] += 1

    return render_template(
        "vendor/analytics.html",
        total_revenue=total_revenue,
        completed_revenue=completed_revenue,
        total_orders=len(all_orders),
        daily_revenue=daily_revenue,
        max_daily=max_daily,
        top_products=top_products,
        top_categories=top_categories,
        max_cat_revenue=max_cat_revenue,
        status_counts=status_counts,
    )


# --------------------------------------------------------------- coupons ----

@vendor_bp.route("/coupons")
@vendor_required
def coupons():
    all_coupons = (
        Coupon.query.filter_by(vendor_id=current_user.id)
        .order_by(Coupon.created_at.desc())
        .all()
    )
    return render_template("vendor/coupons.html", coupons=all_coupons)


@vendor_bp.route("/coupons/add", methods=["GET", "POST"])
@vendor_required
def add_coupon():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        discount_percent = request.form.get("discount_percent", "").strip()
        usage_limit = request.form.get("usage_limit", "0").strip()
        expires_on = request.form.get("expires_on", "").strip()

        if not code or not discount_percent:
            flash("Please enter a coupon code and discount percentage.", "danger")
            return render_template("vendor/coupon_form.html", coupon=None)

        if Coupon.query.filter_by(vendor_id=current_user.id, code=code).first():
            flash("You already have a coupon with this code.", "danger")
            return render_template("vendor/coupon_form.html", coupon=None)

        coupon = Coupon(
            vendor_id=current_user.id,
            code=code,
            discount_percent=max(1, min(90, int(discount_percent))),
            usage_limit=int(usage_limit or 0),
            expires_on=datetime.strptime(expires_on, "%Y-%m-%d").date() if expires_on else None,
        )
        db.session.add(coupon)
        db.session.commit()
        flash(f"Coupon '{code}' created.", "success")
        return redirect(url_for("vendor.coupons"))

    return render_template("vendor/coupon_form.html", coupon=None)


@vendor_bp.route("/coupons/toggle/<int:coupon_id>", methods=["POST"])
@vendor_required
def toggle_coupon(coupon_id):
    coupon = Coupon.query.filter_by(id=coupon_id, vendor_id=current_user.id).first_or_404()
    coupon.is_active = not coupon.is_active
    db.session.commit()
    flash(f"Coupon '{coupon.code}' {'activated' if coupon.is_active else 'deactivated'}.", "info")
    return redirect(url_for("vendor.coupons"))


@vendor_bp.route("/coupons/delete/<int:coupon_id>", methods=["POST"])
@vendor_required
def delete_coupon(coupon_id):
    coupon = Coupon.query.filter_by(id=coupon_id, vendor_id=current_user.id).first_or_404()
    db.session.delete(coupon)
    db.session.commit()
    flash("Coupon deleted.", "info")
    return redirect(url_for("vendor.coupons"))


# -------------------------------------------------------- reviews & invoices ----

@vendor_bp.route("/reviews")
@vendor_required
def reviews():
    all_reviews = (
        Review.query.options(joinedload(Review.product))
        .filter_by(vendor_id=current_user.id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return render_template("vendor/reviews.html", reviews=all_reviews)


@vendor_bp.route("/orders/<int:order_id>/invoice")
@vendor_required
def download_order_invoice(order_id):
    order = Order.query.filter_by(id=order_id, vendor_id=current_user.id).first_or_404()
    pdf = generate_order_invoice_pdf(order, current_user)
    return send_file(
        pdf, mimetype="application/pdf", as_attachment=True,
        download_name=f"invoice_{order.order_code}.pdf",
    )


@vendor_bp.route("/custom-orders/<int:order_id>/invoice")
@vendor_required
def download_custom_order_invoice(order_id):
    custom = CustomOrder.query.filter_by(id=order_id, vendor_id=current_user.id).first_or_404()
    pdf = generate_custom_order_invoice_pdf(custom, current_user)
    return send_file(
        pdf, mimetype="application/pdf", as_attachment=True,
        download_name=f"receipt_{custom.order_code}.pdf",
    )


# ---------------------------------------------------------- notifications ----

@vendor_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@vendor_required
def mark_notification_read(notification_id):
    notif = VendorNotification.query.filter_by(
        id=notification_id, vendor_id=current_user.id
    ).first_or_404()
    notif.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for("vendor.dashboard"))


# ------------------------------------------------------------- CSV export ----

@vendor_bp.route("/export/products.csv")
@vendor_required
def export_products_csv():
    import csv as csv_module
    from flask import Response

    products = Product.query.filter_by(vendor_id=current_user.id).order_by(Product.name).all()

    output = io.StringIO()
    writer = csv_module.writer(output)
    writer.writerow(["Name", "Category", "Price", "Stock", "In Stock", "Featured", "Description"])
    for p in products:
        writer.writerow([
            p.name, p.category.name, p.price,
            p.stock_quantity if p.stock_quantity is not None else "",
            "Yes" if p.in_stock else "No",
            "Yes" if p.is_featured else "No",
            p.description,
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={current_user.slug}-products.csv"},
    )


@vendor_bp.route("/export/orders.csv")
@vendor_required
def export_orders_csv():
    import csv as csv_module
    from flask import Response

    orders = (
        Order.query.filter_by(vendor_id=current_user.id).order_by(Order.created_at.desc()).all()
    )

    output = io.StringIO()
    writer = csv_module.writer(output)
    writer.writerow([
        "Order ID", "Date", "Customer", "Phone", "Product", "Variant", "Qty",
        "Coupon", "Discount", "Delivery Charge", "Total", "Status", "Address",
    ])
    for o in orders:
        writer.writerow([
            o.order_code, o.created_at.strftime("%Y-%m-%d %H:%M"), o.customer_name, o.phone,
            o.product.name, o.variant_label, o.quantity, o.coupon_code,
            o.discount_amount, o.delivery_charge, o.total_price, o.status, o.address,
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={current_user.slug}-orders.csv"},
    )
