-- Migration 005: Create orders table (scoped per vendor)
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    order_code VARCHAR(20) UNIQUE NOT NULL,
    product_id INT NOT NULL,
    variant_id INT,
    variant_label VARCHAR(100),
    customer_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT,
    quantity INT DEFAULT 1,
    coupon_code VARCHAR(30),
    discount_amount DECIMAL(10,2) DEFAULT 0,
    delivery_charge DECIMAL(10,2) DEFAULT 0,
    total_price DECIMAL(10,2) NOT NULL,
    status VARCHAR(30) DEFAULT 'Pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
    -- variant_id intentionally has no FK constraint here since
    -- product_variants is created later (see migration 013) -- the
    -- application enforces the relationship at the ORM level.
);
