from datetime import datetime

from backend.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Integer, default=0)  # Discount as percentage (0-100)
    description = db.Column(db.Text, default="")
    image_filename = db.Column(db.String(255), default="placeholder.png")
    material = db.Column(db.String(150), default="Premium Quality Wool")
    size = db.Column(db.String(100), default="")
    colours = db.Column(db.String(150), default="")
    care = db.Column(db.String(150), default="Dry Clean Only")
    in_stock = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    stock_quantity = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    LOW_STOCK_THRESHOLD = 3

    orders = db.relationship("Order", backref="product", lazy=True)

    @property
    def discounted_price(self):
        """Calculate price after discount"""
        if self.discount_percent and self.discount_percent > 0:
            discount_amount = float(self.price) * (self.discount_percent / 100)
            return float(self.price) - discount_amount
        return float(self.price)

    @property
    def is_low_stock(self):
        return self.in_stock and self.stock_quantity is not None and self.stock_quantity <= self.LOW_STOCK_THRESHOLD

    def __repr__(self):
        return f"<Product {self.name}>"
