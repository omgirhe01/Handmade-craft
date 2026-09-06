from datetime import datetime

from backend.extensions import db


class Testimonial(db.Model):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1-5 stars
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Testimonial {self.customer_name}>"
