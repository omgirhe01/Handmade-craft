from datetime import datetime

from backend.extensions import db


class VendorNotification(db.Model):
    """A short message the platform admin sends to a specific vendor -- shows
    as a dismissible banner across the vendor's dashboard until they mark it
    read."""

    __tablename__ = "vendor_notifications"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vendor = db.relationship(
        "Vendor", backref=db.backref("notifications", lazy=True, cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<VendorNotification vendor={self.vendor_id}>"
