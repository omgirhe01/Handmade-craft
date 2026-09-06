"""
Run this after database/migrate.py (or directly in SQLite demo mode) to load
sample data:

    python database/seed.py

This will:
  1. Create a platform super-admin login -> username: admin | password: admin123
  2. Create a demo vendor (business/user) from the original single-tenant
     sample data -> email: kaku@example.com | password: vendor123
     Store link: /store/kakus-woolen-decor
  3. Add sample categories and products under that vendor so the demo store
     isn't empty.
(Safe to re-run -- it skips anything that already exists.)
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import create_app
from backend.extensions import db
from backend.models import Admin, Category, Coupon, Product, Testimonial, Vendor

CATEGORY_DATA = [
    ("Toran", "toran"),
    ("Flower Decor", "flower-decor"),
    ("Wall Decoration", "wall-decoration"),
    ("Festival Decoration", "festival-decoration"),
    ("Custom Decoration", "custom-decoration"),
]

PRODUCT_DATA = [
    ("Toran (Traditional)", "toran", 450,
     "Beautiful handmade toran for doors and walls. Perfect for festivals, "
     "home decoration and gifting.", "Approx 36 inch", "Red, Green, White, Maroon", True, 12),
    ("Flower Bouquet", "flower-decor", 350,
     "A charming bouquet of handmade flowers, perfect as a gift or a "
     "centrepiece for your living room.", "Approx 12 inch", "Red, Pink, White", True, 2),
    ("Wall Hanging", "wall-decoration", 400,
     "A decorative wall hanging that adds warmth and colour to any wall.",
     "Approx 18 inch", "Multicolour", False, 8),
    ("Flower Pot", "flower-decor", 300,
     "A cheerful flower arrangement in a decorative pot, made entirely by hand.",
     "Approx 10 inch", "Red, Green, Yellow", False, 15),
    ("Diwali Door Hanging", "festival-decoration", 500,
     "Festive door hanging designed especially for Diwali celebrations.",
     "Approx 24 inch", "Red, Gold, Green", True, 6),
    ("Lotus Wall Decor", "wall-decoration", 450,
     "An elegant lotus-inspired wall piece, handcrafted with fine detailing.",
     "Approx 14 inch", "Pink, White, Green", False, 10),
    ("Pom Pom Hanging Decor", "festival-decoration", 350,
     "Colourful pom-pom hanging decor, perfect for festive and everyday decoration.",
     "Approx 20 inch", "Multicolour", False, 3),
]

TESTIMONIAL_DATA = [
    ("Priya Sharma", "Absolutely loved the toran! Exactly what I wanted for Diwali, great quality.", 5),
    ("Ankit Verma", "Fast delivery and beautiful handmade work. Will order again.", 5),
    ("Neha Joshi", "The wall hanging looks even better in person. Highly recommend!", 4),
]


def run():
    app = create_app()
    with app.app_context():
        # Safe to call even if database/migrate.py already created the tables
        # (create_all only creates tables that don't exist yet). This also
        # means the SQLite quick-demo mode works without running migrate.py,
        # since MySQL-specific migration SQL isn't SQLite-compatible.
        db.create_all()

        if not Admin.query.filter_by(username="admin").first():
            admin = Admin(username="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            print("Created platform admin -> username: admin | password: admin123")

        vendor = Vendor.query.filter_by(slug="kakus-woolen-decor").first()
        if not vendor:
            vendor = Vendor(
                email="kaku@example.com",
                owner_name="Kaku",
                business_name="Kaku's Woolen Decor",
                slug="kakus-woolen-decor",
                tagline="Handmade with Love",
                about_text=(
                    "Kaku's Woolen Decor is a small home-based handmade business. "
                    "We create beautiful decoration items with creativity, patience "
                    "and love."
                ),
                story=(
                    "It all started as a hobby making woolen toran for our own home "
                    "during festivals -- friends and family loved them so much that "
                    "it slowly turned into a small handmade business."
                ),
                phone_number="+91 98765 43210",
                whatsapp_number="919876543210",
                contact_email="kakuswoolendecor@gmail.com",
                address="Akola, Maharashtra, India",
                is_active=True,
            )
            vendor.set_password("vendor123")
            db.session.add(vendor)
            db.session.flush()
            print(
                "Created demo vendor -> email: kaku@example.com | password: vendor123\n"
                "Store link: /store/kakus-woolen-decor"
            )

        slug_to_category = {}
        for name, slug in CATEGORY_DATA:
            category = Category.query.filter_by(vendor_id=vendor.id, slug=slug).first()
            if not category:
                category = Category(vendor_id=vendor.id, name=name, slug=slug)
                db.session.add(category)
                db.session.flush()
            slug_to_category[slug] = category

        if Product.query.filter_by(vendor_id=vendor.id).count() == 0:
            for name, cat_slug, price, description, size, colours, featured, stock in PRODUCT_DATA:
                db.session.add(
                    Product(
                        vendor_id=vendor.id,
                        name=name,
                        category_id=slug_to_category[cat_slug].id,
                        price=price,
                        description=description,
                        size=size,
                        colours=colours,
                        is_featured=featured,
                        stock_quantity=stock,
                    )
                )
            print(f"Added {len(PRODUCT_DATA)} sample products to the demo vendor.")

        if not vendor.announcement_text:
            vendor.announcement_text = "🎉 Festive Season Sale — Order now for on-time Diwali delivery!"

        if Testimonial.query.filter_by(vendor_id=vendor.id).count() == 0:
            for customer_name, message, rating in TESTIMONIAL_DATA:
                db.session.add(
                    Testimonial(
                        vendor_id=vendor.id,
                        customer_name=customer_name,
                        message=message,
                        rating=rating,
                    )
                )
            print(f"Added {len(TESTIMONIAL_DATA)} sample testimonials to the demo vendor.")

        if not Coupon.query.filter_by(vendor_id=vendor.id, code="WELCOME10").first():
            db.session.add(
                Coupon(vendor_id=vendor.id, code="WELCOME10", discount_percent=10, usage_limit=0)
            )
            print("Added sample coupon -> WELCOME10 (10% off)")

        db.session.commit()
        print("Database seeded successfully.")


if __name__ == "__main__":
    run()
