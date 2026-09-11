-- Migration: Add missing coupon and delivery fields to orders table
-- NOTE: "ADD COLUMN IF NOT EXISTS" was removed below -- it isn't valid
-- syntax on all MySQL/MariaDB versions ("IF NOT EXISTS" for ADD COLUMN
-- needs MySQL 8.0.29+; older servers throw a syntax error, which is what
-- was blocking this migration from ever running). Since this migration
-- never succeeded before, these columns don't exist yet, so a plain
-- ADD COLUMN is safe here.
ALTER TABLE orders
ADD COLUMN coupon_code VARCHAR(50) NULL AFTER quantity,
ADD COLUMN discount_amount DECIMAL(10, 2) DEFAULT 0.00 AFTER coupon_code,
ADD COLUMN delivery_charge DECIMAL(10, 2) DEFAULT 0.00 AFTER discount_amount;
