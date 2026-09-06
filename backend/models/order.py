import random
import string
from datetime import datetime

from backend.extensions import db


def generate_order_code():
    return "ORD" + "".join(random.choices(string.digits, k=4))


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    order_code = db.Column(db.String(20), unique=True, default=generate_order_code)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, default="")
    quantity = db.Column(db.Integer, default=1)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Order {self.order_code}>"
