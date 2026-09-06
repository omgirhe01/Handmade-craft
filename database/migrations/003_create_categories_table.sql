-- Migration 003: Create categories table (scoped per vendor)
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    UNIQUE KEY uq_category_vendor_slug (vendor_id, slug),
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE
);
