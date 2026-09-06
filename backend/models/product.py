from datetime import datetime

from backend.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text, default="")
    image_filename = db.Column(db.String(255), default="placeholder.png")
    material = db.Column(db.String(150), default="Premium Quality Wool")
    size = db.Column(db.String(100), default="")
    colours = db.Column(db.String(150), default="")
    care = db.Column(db.String(150), default="Dry Clean Only")
    in_stock = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="product", lazy=True)

    def __repr__(self):
        return f"<Product {self.name}>"
