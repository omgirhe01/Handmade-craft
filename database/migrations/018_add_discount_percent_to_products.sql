-- Migration 018: Add discount_percent field to products table
-- This allows vendors to set discount percentages for products

ALTER TABLE products
ADD COLUMN discount_percent INTEGER DEFAULT 0 AFTER price;
