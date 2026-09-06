-- Migration 002: Create vendors table (business-owner "users", each with
-- their own storefront reachable at /store/<slug>)
CREATE TABLE IF NOT EXISTS vendors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    owner_name VARCHAR(150) NOT NULL,
    business_name VARCHAR(150) NOT NULL,
    slug VARCHAR(150) UNIQUE NOT NULL,
    tagline VARCHAR(200) DEFAULT 'Handmade with Love',
    story TEXT,
    about_text TEXT,
    phone_number VARCHAR(20),
    whatsapp_number VARCHAR(20),
    contact_email VARCHAR(150),
    address VARCHAR(255),
    instagram_url VARCHAR(255),
    facebook_url VARCHAR(255),
    logo_filename VARCHAR(255),
    cover_filename VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
