-- Migration 003: Create products table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category_id INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    description TEXT,
    image_filename VARCHAR(255) DEFAULT 'placeholder.png',
    material VARCHAR(150) DEFAULT 'Premium Quality Wool',
    size VARCHAR(100),
    colours VARCHAR(150),
    care VARCHAR(150) DEFAULT 'Dry Clean Only',
    in_stock BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
