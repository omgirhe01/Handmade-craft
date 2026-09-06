from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from backend.extensions import db
from backend.models import Category, ContactMessage, CustomOrder, Order, Product, Vendor

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
        Product.query.filter_by(vendor_id=g.vendor.id, in_stock=True)
        .order_by(Product.created_at.desc())
        .limit(8)
        .all()
    )
    categories = Category.query.filter_by(vendor_id=g.vendor.id).all()
    return render_template("home.html", featured=featured, categories=categories)


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


@public_bp.route("/order/<int:product_id>", methods=["GET", "POST"])
def place_order(product_id):
    product = Product.query.filter_by(id=product_id, vendor_id=g.vendor.id).first_or_404()

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        try:
            quantity = max(1, int(request.form.get("quantity", 1)))
        except ValueError:
            quantity = 1

        if not customer_name or not phone:
            flash("Please enter your name and mobile number.", "danger")
            return render_template("order_form.html", product=product)

        order = Order(
            vendor_id=g.vendor.id,
            product_id=product.id,
            customer_name=customer_name,
            phone=phone,
            address=address,
            quantity=quantity,
            total_price=product.price * quantity,
        )
        db.session.add(order)
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
