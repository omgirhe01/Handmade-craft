-- Migration: Add missing coupon and delivery fields to orders table
ALTER TABLE orders 
ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(50) NULL AFTER quantity,
ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10, 2) DEFAULT 0.00 AFTER coupon_code,
ADD COLUMN IF NOT EXISTS delivery_charge DECIMAL(10, 2) DEFAULT 0.00 AFTER discount_amount;