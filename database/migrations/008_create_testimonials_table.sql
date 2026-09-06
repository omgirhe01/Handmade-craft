-- Migration 008: Create testimonials table (vendor-curated quotes shown on
-- their store home page)
CREATE TABLE IF NOT EXISTS testimonials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    rating INT DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE
);
