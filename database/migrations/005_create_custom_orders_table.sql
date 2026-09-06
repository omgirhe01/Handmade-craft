-- Migration 005: Create custom_orders table
CREATE TABLE IF NOT EXISTS custom_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_code VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    item_type VARCHAR(100) NOT NULL,
    preferred_colours VARCHAR(150),
    size VARCHAR(100),
    quantity INT DEFAULT 1,
    design_requirements TEXT,
    required_date VARCHAR(30),
    status VARCHAR(30) DEFAULT 'Pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
