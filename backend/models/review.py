from datetime import datetime

from backend.extensions import db


class Review(db.Model):
    """A customer's review of a product, left after their order is placed.
    Tied to the specific Order so a customer can only review something they
    actually ordered."""

    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), unique=True, nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1-5 stars
    comment = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product", backref=db.backref("reviews", lazy=True))
    order = db.relationship("Order", backref=db.backref("review", uselist=False))

    def __repr__(self):
        return f"<Review {self.customer_name} - {self.rating}★>"
