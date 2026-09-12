import os

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from backend.extensions import db
from backend.models import (
    Category,
    ContactMessage,
    Coupon,
    CustomOrder,
    Order,
    Product,
    ProductVariant,
    Review,
    Testimonial,
    Vendor,
)
from backend.utils.helpers import image_url
from backend.utils.invoice import generate_custom_order_invoice_pdf, generate_order_invoice_pdf
from sqlalchemy.orm import joinedload

# url_prefix="/store/<string:slug>" is set when this blueprint is registered
# in backend/__init__.py. Every route below is automatically scoped to one
# vendor's storefront via g.vendor (loaded in the before_request hook).
public_bp = Blueprint("public", __name__)


@public_bp.url_value_preprocessor
def pull_slug(endpoint, values):
    g.vendor_slug = values.pop("slug", None)


@public_bp.url_defaults
def add_slug(endpoint, values):
    # So every url_for('public.xxx', ...) call inside this blueprint's own
    # templates doesn't need to pass slug explicitly - it's added back here.
    if "slug" in values or not g.get("vendor_slug"):
        return
    if endpoint.startswith("public."):
        values["slug"] = g.vendor_slug


@public_bp.before_request
def load_vendor():
    vendor = Vendor.query.filter_by(slug=g.vendor_slug, is_active=True).first()
    if not vendor:
        abort(404)
    g.vendor = vendor
    if vendor.is_maintenance:
        return render_template("maintenance.html"), 503


@public_bp.context_processor
def inject_vendor_settings():
    v = g.get("vendor")
    if not v:
        return {}
    return {
        "VENDOR": v,
        "SITE_NAME": v.business_name,
        "SITE_TAGLINE": v.tagline,
        "WHATSAPP_NUMBER": v.whatsapp_number or v.phone_number,
        "PHONE_NUMBER": v.phone_number,
        "EMAIL": v.contact_email,
        "ADDRESS": v.address,
    }


@public_bp.route("/favicon-circle/<path:stored_value>")
def vendor_favicon(stored_value):
    """Serves a locally-stored vendor logo cropped to a circle with a
    transparent background, so it shows as a clean round icon in the
    browser tab instead of a plain square. Cloudinary-hosted logos never
    hit this route -- favicon_url() sends those straight to Cloudinary's
    own on-the-fly transformation instead."""
    import io

    from PIL import Image, ImageDraw

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_value)
    if not os.path.isfile(path):
        abort(404)

    with Image.open(path) as img:
        img = img.convert("RGBA")
        w, h = img.size
        side = min(w, h)
        left, top = (w - side) // 2, (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        img = img.resize((128, 128), Image.LANCZOS)

        mask = Image.new("L", (128, 128), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 128, 128), fill=255)

        circled = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        circled.paste(img, (0, 0), mask=mask)

        buf = io.BytesIO()
        circled.save(buf, format="PNG")
        buf.seek(0)

    response = send_file(buf, mimetype="image/png")
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@public_bp.route("/")
def home():
    featured = (
        Product.query.options(joinedload(Product.category))
        .filter_by(vendor_id=g.vendor.id, in_stock=True, is_featured=True)
        .order_by(Product.created_at.desc())
        .limit(8)
        .all()
    )
    if not featured:
        featured = (
            Product.query.options(joinedload(Product.category))
            .filter_by(vendor_id=g.vendor.id, in_stock=True)
            .order_by(Product.created_at.desc())
            .limit(8)
            .all()
        )
    categories = Category.query.filter_by(vendor_id=g.vendor.id).all()
    testimonials = (
        Testimonial.query.filter_by(vendor_id=g.vendor.id)
        .order_by(Testimonial.created_at.desc())
        .limit(6)
        .all()
    )
    return render_template(
        "home.html", featured=featured, categories=categories, testimonials=testimonials
    )


@public_bp.route("/products")
def products():
    category_slug = request.args.get("category")
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "")
    page = request.args.get("page", 1, type=int)

    query = Product.query.options(joinedload(Product.category)).filter_by(vendor_id=g.vendor.id)
    if category_slug and category_slug != "all":
        query = query.join(Category).filter(Category.slug == category_slug)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    all_products = query.paginate(page=page, per_page=20, error_out=False)
    categories = Category.query.filter_by(vendor_id=g.vendor.id).all()
    return render_template(
        "products.html",
        products=all_products.items,
        pagination=all_products,
        categories=categories,
        active_category=category_slug or "all",
        search=search,
        sort=sort,
    )


@public_bp.route("/products/<int:product_id>")
def product_detail(product_id):
    product = Product.query.filter_by(id=product_id, vendor_id=g.vendor.id).first_or_404()

    # "Frequently bought together": look at other customers who ordered this
    # product and see what else they ordered. Falls back to same-category
    # products when there isn't enough order history yet (e.g. a new store).
    co_purchased_ids = (
        db.session.query(Order.product_id)
        .filter(
            Order.vendor_id == g.vendor.id,
            Order.product_id != product.id,
            Order.phone.in_(
                db.session.query(Order.phone).filter(
                    Order.vendor_id == g.vendor.id, Order.product_id == product.id
                )
            ),
        )
        .distinct()
        .limit(4)
        .all()
    )
    co_purchased_ids = [row[0] for row in co_purchased_ids]

    related = []
    if co_purchased_ids:
        related = Product.query.options(joinedload(Product.category)).filter(
            Product.id.in_(co_purchased_ids), Product.vendor_id == g.vendor.id
        ).all()

    if len(related) < 4:
        exclude_ids = [product.id] + [p.id for p in related]
        fallback = (
            Product.query.options(joinedload(Product.category))
            .filter(
                Product.category_id == product.category_id,
                Product.id.notin_(exclude_ids),
                Product.vendor_id == g.vendor.id,
            )
            .limit(4 - len(related))
            .all()
        )
        related = related + fallback

    return render_template(
        "product_detail.html", product=product, related=related, has_copurchase=bool(co_purchased_ids)
    )


@public_bp.route("/coupon/check/<int:product_id>", methods=["POST"])
def check_coupon(product_id):
    """AJAX endpoint used by the order form's 'Apply' button -- validates a
    coupon code live and returns the discount, without placing an order."""
    product = Product.query.filter_by(id=product_id, vendor_id=g.vendor.id).first_or_404()
    code = (request.form.get("coupon_code") or "").strip().upper()
    variant_id = request.form.get("variant_id", "").strip()
    try:
        quantity = max(1, int(request.form.get("quantity", 1)))
    except ValueError:
        quantity = 1

    unit_price = float(product.price)
    if variant_id:
        variant = ProductVariant.query.filter_by(id=int(variant_id), product_id=product.id).first()
        if variant:
            unit_price = float(variant.price)

    subtotal = unit_price * quantity
    delivery_charge = float(g.vendor.delivery_charge or 0)

    # Product's own discount (only applies when no variant is selected --
    # variants carry their own fixed price and are not discounted further).
    product_discount_amount = 0.0
    if not variant_id and product.discount_percent and product.discount_percent > 0:
        product_discount_amount = round(subtotal * product.discount_percent / 100, 2)
    subtotal_after_product_discount = subtotal - product_discount_amount

    if not code:
        return jsonify({"valid": False, "message": "Enter a coupon code first."})

    coupon = Coupon.query.filter_by(vendor_id=g.vendor.id, code=code).first()
    if not coupon or not coupon.is_valid():
        return jsonify({"valid": False, "message": "This coupon code is not valid."})

    discount_amount = round(subtotal_after_product_discount * coupon.discount_percent / 100, 2)
    final_total = round(subtotal_after_product_discount - discount_amount + delivery_charge, 2)

    return jsonify({
        "valid": True,
        "discount_percent": coupon.discount_percent,
        "subtotal": subtotal,
        "product_discount_amount": product_discount_amount,
        "discount_amount": discount_amount,
        "delivery_charge": delivery_charge,
        "final_total": final_total,
        "message": f"Coupon applied! {coupon.discount_percent}% off.",
    })


@public_bp.route("/order/<int:product_id>", methods=["GET", "POST"])
def place_order(product_id):
    product = Product.query.filter_by(id=product_id, vendor_id=g.vendor.id).first_or_404()

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        coupon_input = request.form.get("coupon_code", "").strip()
        variant_id = request.form.get("variant_id", "").strip()
        try:
            quantity = max(1, int(request.form.get("quantity", 1)))
        except ValueError:
            quantity = 1

        if not customer_name or not phone:
            flash("Please enter your name and mobile number.", "danger")
            return render_template("order_form.html", product=product)

        variant = None
        unit_price = float(product.price)
        if variant_id:
            variant = ProductVariant.query.filter_by(id=int(variant_id), product_id=product.id).first()
            if variant:
                unit_price = float(variant.price)
        elif product.variants:
            flash("Please choose an option before ordering.", "danger")
            return render_template("order_form.html", product=product)

        subtotal = unit_price * quantity

        # Product's own discount (only when no variant selected -- variants
        # have their own fixed price and aren't discounted further).
        product_discount_amount = 0.0
        if not variant_id and product.discount_percent and product.discount_percent > 0:
            product_discount_amount = (subtotal * product.discount_percent) / 100
        subtotal_after_product_discount = subtotal - product_discount_amount

        coupon_discount_amount = 0.0
        applied_coupon = ""

        if coupon_input:
            coupon = Coupon.query.filter_by(vendor_id=g.vendor.id, code=coupon_input.upper()).first()
            if coupon and coupon.is_valid():
                coupon_discount_amount = (subtotal_after_product_discount * coupon.discount_percent) / 100
                applied_coupon = coupon.code
                coupon.times_used += 1
            else:
                flash("That coupon code is invalid or has expired.", "danger")
                return render_template("order_form.html", product=product)

        discount_amount = product_discount_amount + coupon_discount_amount

        delivery_charge = float(g.vendor.delivery_charge or 0)

        order = Order(
            vendor_id=g.vendor.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            variant_label=variant.label if variant else "",
            customer_name=customer_name,
            phone=phone,
            address=address,
            quantity=quantity,
            coupon_code=applied_coupon,
            discount_amount=discount_amount,
            delivery_charge=delivery_charge,
            total_price=subtotal - discount_amount + delivery_charge,
        )
        db.session.add(order)

        if variant:
            variant.stock_quantity = max(0, (variant.stock_quantity or 0) - quantity)
        elif product.stock_quantity is not None:
            product.stock_quantity = max(0, product.stock_quantity - quantity)
            if product.stock_quantity == 0:
                product.in_stock = False

        db.session.commit()
        session[f"phone_{g.vendor.id}"] = phone
        flash(f"Order placed! Your Order ID is {order.order_code}.", "success")
        return redirect(url_for("public.my_orders"))

    return render_template("order_form.html", product=product)


@public_bp.route("/custom-order", methods=["GET", "POST"])
def custom_order():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        item_type = request.form.get("item_type", "").strip()

        if not full_name or not mobile or not item_type:
            flash("Please fill in all required fields.", "danger")
            return render_template("custom_order.html")

        custom = CustomOrder(
            vendor_id=g.vendor.id,
            full_name=full_name,
            mobile=mobile,
            item_type=item_type,
            preferred_colours=request.form.get("preferred_colours", "").strip(),
            size=request.form.get("size", "").strip(),
            quantity=max(1, int(request.form.get("quantity") or 1)),
            design_requirements=request.form.get("design_requirements", "").strip(),
            required_date=request.form.get("required_date", "").strip(),
        )
        db.session.add(custom)
        db.session.commit()
        session[f"phone_{g.vendor.id}"] = mobile
        flash(f"Custom order submitted! Your Order ID is {custom.order_code}.", "success")
        return redirect(url_for("public.my_orders"))

    return render_template("custom_order.html")


@public_bp.route("/my-orders", methods=["GET", "POST"])
def my_orders():
    # NOTE: we intentionally do NOT read the remembered phone number from the
    # session on a plain page load/refresh. This page is often opened on a
    # shared/public device -- if we auto-filled the last searched number on
    # every GET, the next visitor hitting refresh (or just opening this page)
    # would see the previous customer's order status. So every visit starts
    # blank; results only appear right after an explicit search (POST).
    # We still WRITE the phone to the session on search so that the
    # cancel/review/invoice actions on this same page load can verify the
    # order belongs to the person who just searched for it.
    orders = []
    custom_orders = []
    searched = False
    phone = ""
    session_key = f"phone_{g.vendor.id}"

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        if phone:
            session[session_key] = phone

    if phone:
        searched = True
        orders = (
            Order.query.options(joinedload(Order.product), joinedload(Order.review))
            .filter_by(phone=phone, vendor_id=g.vendor.id)
            .order_by(Order.created_at.desc())
            .all()
        )
        custom_orders = (
            CustomOrder.query.filter_by(mobile=phone, vendor_id=g.vendor.id)
            .order_by(CustomOrder.created_at.desc())
            .all()
        )

    return render_template(
        "my_orders.html",
        orders=orders,
        custom_orders=custom_orders,
        searched=searched,
        remembered_phone=phone,
    )


@public_bp.route("/order/<int:order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, vendor_id=g.vendor.id).first_or_404()
    session_phone = session.get(f"phone_{g.vendor.id}", "")

    # Only the customer who placed it (matched via their remembered phone
    # number) can cancel it, and only while it's still Pending.
    if order.phone != session_phone:
        flash("We couldn't verify this order belongs to you.", "danger")
    elif order.status != "Pending":
        flash("This order can no longer be cancelled -- it's already being processed.", "danger")
    else:
        order.status = "Cancelled"
        if order.variant:
            order.variant.stock_quantity = (order.variant.stock_quantity or 0) + order.quantity
        elif order.product.stock_quantity is not None:
            order.product.stock_quantity += order.quantity
            order.product.in_stock = True
        db.session.commit()
        flash(f"Order #{order.order_code} has been cancelled.", "info")

    return redirect(url_for("public.my_orders"))


@public_bp.route("/custom-order/<int:order_id>/cancel", methods=["POST"])
def cancel_custom_order(order_id):
    custom = CustomOrder.query.filter_by(id=order_id, vendor_id=g.vendor.id).first_or_404()
    session_phone = session.get(f"phone_{g.vendor.id}", "")

    if custom.mobile != session_phone:
        flash("We couldn't verify this order belongs to you.", "danger")
    elif custom.status != "Pending":
        flash("This order can no longer be cancelled -- it's already being processed.", "danger")
    else:
        custom.status = "Cancelled"
        db.session.commit()
        flash(f"Custom order #{custom.order_code} has been cancelled.", "info")

    return redirect(url_for("public.my_orders"))


@public_bp.route("/order/<int:order_id>/invoice")
def download_invoice(order_id):
    order = Order.query.filter_by(id=order_id, vendor_id=g.vendor.id).first_or_404()
    if order.phone != session.get(f"phone_{g.vendor.id}"):
        abort(403)
    pdf = generate_order_invoice_pdf(order, g.vendor)
    return send_file(
        pdf, mimetype="application/pdf", as_attachment=True,
        download_name=f"invoice_{order.order_code}.pdf",
    )


@public_bp.route("/custom-order/<int:order_id>/invoice")
def download_custom_order_invoice(order_id):
    custom = CustomOrder.query.filter_by(id=order_id, vendor_id=g.vendor.id).first_or_404()
    if custom.mobile != session.get(f"phone_{g.vendor.id}"):
        abort(403)
    pdf = generate_custom_order_invoice_pdf(custom, g.vendor)
    return send_file(
        pdf, mimetype="application/pdf", as_attachment=True,
        download_name=f"receipt_{custom.order_code}.pdf",
    )


@public_bp.route("/review/<int:order_id>", methods=["GET", "POST"])
def leave_review(order_id):
    order = Order.query.filter_by(id=order_id, vendor_id=g.vendor.id).first_or_404()

    if order.phone != session.get(f"phone_{g.vendor.id}"):
        abort(403)
    if order.status != "Completed":
        flash("You can leave a review once your order is marked Completed.", "warning")
        return redirect(url_for("public.my_orders"))
    if order.review:
        flash("You've already reviewed this order.", "info")
        return redirect(url_for("public.my_orders"))

    if request.method == "POST":
        rating = max(1, min(5, int(request.form.get("rating") or 5)))
        comment = request.form.get("comment", "").strip()
        db.session.add(
            Review(
                vendor_id=g.vendor.id,
                product_id=order.product_id,
                order_id=order.id,
                customer_name=order.customer_name,
                rating=rating,
                comment=comment,
            )
        )
        db.session.commit()
        flash("Thanks for your review!", "success")
        return redirect(url_for("public.my_orders"))

    return render_template("leave_review.html", order=order)


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not message:
            flash("Please enter your name and message.", "danger")
        else:
            msg = ContactMessage(
                vendor_id=g.vendor.id,
                name=name,
                email=request.form.get("email", "").strip(),
                phone=request.form.get("phone", "").strip(),
                message=message,
            )
            db.session.add(msg)
            db.session.commit()
            flash("Thank you! Your message has been sent.", "success")
            return redirect(url_for("public.contact"))

    return render_template("contact.html")


@public_bp.route("/set-language/<lang>")
def set_language(lang):
    if lang in ("en", "hi"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("public.home"))


@public_bp.route("/about")
def about():
    return render_template("about.html")


@public_bp.route("/api/products-by-ids")
def products_by_ids():
    ids_param = request.args.get("ids", "")
    try:
        ids = [int(x) for x in ids_param.split(",") if x.strip().isdigit()]
    except ValueError:
        ids = []

    if not ids:
        return jsonify({"products": []})

    products = Product.query.filter(
        Product.id.in_(ids), Product.vendor_id == g.vendor.id
    ).all()

    return jsonify({
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "image_url": image_url(p.image_filename),
                "in_stock": p.in_stock,
                "url": url_for("public.product_detail", product_id=p.id),
            }
            for p in products
        ]
    })
