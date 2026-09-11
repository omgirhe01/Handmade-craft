from datetime import datetime

from backend.extensions import db
from backend.models.order import generate_order_code


class CustomOrder(db.Model):
    __tablename__ = "custom_orders"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    order_code = db.Column(db.String(20), unique=True, default=generate_order_code)
    full_name = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(20), nullable=False, index=True)
    item_type = db.Column(db.String(100), nullable=False)
    preferred_colours = db.Column(db.String(150), default="")
    size = db.Column(db.String(100), default="")
    quantity = db.Column(db.Integer, default=1)
    design_requirements = db.Column(db.Text, default="")
    required_date = db.Column(db.String(30), default="")
    status = db.Column(db.String(30), default="Pending", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<CustomOrder {self.order_code}>"
