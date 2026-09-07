from flask import (
    Blueprint,
    abort,
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
    Review,
    Testimonial,
    Vendor,
)
from backend.utils.invoice import generate_custom_order_invoice_pdf, generate_order_invoice_pdf

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


@public_bp.route("/")
def home():
    featured = (
        Product.query.filter_by(vendor_id=g.vendor.id, in_stock=True, is_featured=True)
        .order_by(Product.created_at.desc())
        .limit(8)
        .all()
    )
    if not featured:
        featured = (
            Product.query.filter_by(vendor_id=g.vendor.id, in_stock=True)
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

    query = Product.query.filter_by(vendor_id=g.vendor.id)
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

    all_products = query.all()
    categories = Category.query.filter_by(vendor_id=g.vendor.id).all()
    return render_template(
        "products.html",
        products=all_products,
        categories=categories,
        active_category=category_slug or "all",
        search=search,
        sort=sort,
    )


@public_bp.route("/products/<int:product_id>")
def product_detail(product_id):
    product = Product.query.filter_by(id=product_id, vendor_id=g.vendor.id).first_or_404()
    related = (
        Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.vendor_id == g.vendor.id,
        )
        .limit(4)
        .all()
    )
    return render_template("product_detail.html", product=product, related=related)


@public_bp.route("/coupon/check/<int:product_id>", methods=["POST"])
def check_coupon(product_id):
    """AJAX endpoint used by the order form's 'Apply' button -- validates a
    coupon code live and returns the discount, without placing an order."""
    product = Product.query.filter_by(id=product_id, vendor_id=g.vendor.id).first_or_404()
    code = (request.form.get("coupon_code") or "").strip().upper()
    try:
        quantity = max(1, int(request.form.get("quantity", 1)))
    except ValueError:
        quantity = 1

    subtotal = float(product.price) * quantity

    if not code:
        return jsonify({"valid": False, "message": "Enter a coupon code first."})

    coupon = Coupon.query.filter_by(vendor_id=g.vendor.id, code=code).first()
    if not coupon or not coupon.is_valid():
        return jsonify({"valid": False, "message": "This coupon code is not valid."})

    discount_amount = round(subtotal * coupon.discount_percent / 100, 2)
    final_total = round(subtotal - discount_amount, 2)

    return jsonify({
        "valid": True,
        "discount_percent": coupon.discount_percent,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
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
        try:
            quantity = max(1, int(request.form.get("quantity", 1)))
        except ValueError:
            quantity = 1

        if not customer_name or not phone:
            flash("Please enter your name and mobile number.", "danger")
            return render_template("order_form.html", product=product)

        subtotal = product.price * quantity
        discount_amount = 0
        applied_coupon = ""

        if coupon_input:
            coupon = Coupon.query.filter_by(vendor_id=g.vendor.id, code=coupon_input.upper()).first()
            if coupon and coupon.is_valid():
                discount_amount = (subtotal * coupon.discount_percent) / 100
                applied_coupon = coupon.code
                coupon.times_used += 1
            else:
                flash("That coupon code is invalid or has expired.", "danger")
                return render_template("order_form.html", product=product)

        order = Order(
            vendor_id=g.vendor.id,
            product_id=product.id,
            customer_name=customer_name,
            phone=phone,
            address=address,
            quantity=quantity,
            coupon_code=applied_coupon,
            discount_amount=discount_amount,
            total_price=subtotal - discount_amount,
        )
        db.session.add(order)

        if product.stock_quantity is not None:
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
    orders = []
    custom_orders = []
    searched = False
    session_key = f"phone_{g.vendor.id}"
    phone = session.get(session_key, "")

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        if phone:
            session[session_key] = phone

    if phone:
        searched = True
        orders = (
            Order.query.filter_by(phone=phone, vendor_id=g.vendor.id)
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


@public_bp.route("/about")
def about():
    return render_template("about.html")
