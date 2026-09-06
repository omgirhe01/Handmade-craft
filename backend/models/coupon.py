from datetime import datetime

from backend.extensions import db


class Coupon(db.Model):
    """A discount code a vendor can create; customers enter it at checkout
    on the order form to get a percentage off."""

    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)  # e.g. 10 for 10% off
    is_active = db.Column(db.Boolean, default=True)
    usage_limit = db.Column(db.Integer, default=0)  # 0 = unlimited
    times_used = db.Column(db.Integer, default=0)
    expires_on = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("vendor_id", "code", name="uq_coupon_vendor_code"),
    )

    def is_valid(self):
        if not self.is_active:
            return False
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
        if self.expires_on and self.expires_on < datetime.utcnow().date():
            return False
        return True

    def __repr__(self):
        return f"<Coupon {self.code} ({self.discount_percent}%)>"
