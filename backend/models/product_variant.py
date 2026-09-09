from backend.extensions import db


class ProductVariant(db.Model):
    """An optional size/colour option for a product with its own price and
    stock (e.g. 'Small - Red' at ₹200, 'Large - Blue' at ₹350). If a product
    has no variants, it's sold at its plain base price as before.
    """

    __tablename__ = "product_variants"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    label = db.Column(db.String(100), nullable=False)  # e.g. "Small - Red"
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=10)
    position = db.Column(db.Integer, default=0)

    product = db.relationship(
        "Product", backref=db.backref("variants", lazy=True, cascade="all, delete-orphan", order_by="ProductVariant.position")
    )

    def __repr__(self):
        return f"<ProductVariant {self.label}>"
