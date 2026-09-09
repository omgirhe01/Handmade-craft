from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db


class Vendor(UserMixin, db.Model):
    """A business owner ("user") who runs their own handmade-goods storefront
    on the platform. Each vendor gets a unique slug -> unique public link
    (e.g. /store/<slug>) that they can share on Instagram / Facebook / WhatsApp.
    """

    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True)

    # Login
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    owner_name = db.Column(db.String(150), nullable=False)

    # Store identity
    business_name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    tagline = db.Column(db.String(200), default="Handmade with Love")

    # Customisable content
    story = db.Column(db.Text, default="")
    about_text = db.Column(db.Text, default="")

    # Contact / social (shown on their public store)
    phone_number = db.Column(db.String(20), default="")
    whatsapp_number = db.Column(db.String(20), default="")
    contact_email = db.Column(db.String(150), default="")
    address = db.Column(db.String(255), default="")
    instagram_url = db.Column(db.String(255), default="")
    facebook_url = db.Column(db.String(255), default="")

    # Branding images (stored as "<slug>/<filename>" under the uploads folder)
    logo_filename = db.Column(db.String(255), default="")
    cover_filename = db.Column(db.String(255), default="")
    story_image_filename = db.Column(db.String(255), default="")
    upi_qr_filename = db.Column(db.String(255), default="")

    delivery_charge = db.Column(db.Numeric(10, 2), default=0)
    custom_domain = db.Column(db.String(255), unique=True, nullable=True)

    # Store personalisation
    theme_color = db.Column(db.String(10), default="#5E1836")
    announcement_text = db.Column(db.String(200), default="")
    meta_description = db.Column(db.String(300), default="")

    is_active = db.Column(db.Boolean, default=True)
    is_maintenance = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    categories = db.relationship(
        "Category", backref="vendor", lazy=True, cascade="all, delete-orphan"
    )
    products = db.relationship(
        "Product", backref="vendor", lazy=True, cascade="all, delete-orphan"
    )
    orders = db.relationship(
        "Order", backref="vendor", lazy=True, cascade="all, delete-orphan"
    )
    custom_orders = db.relationship(
        "CustomOrder", backref="vendor", lazy=True, cascade="all, delete-orphan"
    )
    contact_messages = db.relationship(
        "ContactMessage", backref="vendor", lazy=True, cascade="all, delete-orphan"
    )
    testimonials = db.relationship(
        "Testimonial", backref="vendor", lazy=True, cascade="all, delete-orphan"
    )
    coupons = db.relationship(
        "Coupon", backref="vendor", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Prefix the id so the shared Flask-Login user_loader can tell a Vendor
    # apart from an Admin (both use the same login manager/session).
    def get_id(self):
        return f"vendor:{self.id}"

    def __repr__(self):
        return f"<Vendor {self.business_name} ({self.slug})>"
