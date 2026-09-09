-- Migration: Add variant columns to orders table
ALTER TABLE orders 
ADD COLUMN variant_id INT NULL AFTER product_id,
ADD COLUMN variant_label VARCHAR(255) NULL AFTER variant_id;