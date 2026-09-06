-- Migration 011: Create coupons table (vendor discount codes)
CREATE TABLE IF NOT EXISTS coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    code VARCHAR(30) NOT NULL,
    discount_percent INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    usage_limit INT DEFAULT 0,
    times_used INT DEFAULT 0,
    expires_on DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_coupon_vendor_code (vendor_id, code),
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE
);
