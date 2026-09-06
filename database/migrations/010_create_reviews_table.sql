-- Migration 010: Create reviews table (customer reviews tied to a verified
-- completed order)
CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    product_id INT NOT NULL,
    order_id INT UNIQUE NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    rating INT DEFAULT 5,
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);
