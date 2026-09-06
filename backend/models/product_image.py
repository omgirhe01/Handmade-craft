from backend.extensions import db


class ProductImage(db.Model):
    """An extra photo for a product's gallery (in addition to the main
    Product.image_filename, which stays as the primary/cover photo)."""

    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    position = db.Column(db.Integer, default=0)

    product = db.relationship(
        "Product", backref=db.backref("gallery_images", lazy=True, cascade="all, delete-orphan", order_by="ProductImage.position")
    )

    def __repr__(self):
        return f"<ProductImage {self.image_filename}>"
