-- Migration 019: Speed up the storefront's product listing queries.
--
-- The home page ("featured products") and /products page both filter by
-- vendor_id + in_stock (+ is_featured on the home page) and then sort by
-- created_at. vendor_id alone is already indexed (InnoDB auto-indexes
-- foreign key columns), but MySQL can only use ONE index per table per
-- query, so filtering on vendor_id AND in_stock/is_featured AND sorting by
-- created_at was still doing extra row-by-row work on every visit.
-- These composite indexes let MySQL satisfy the whole filter+sort from the
-- index itself instead of scanning every one of a vendor's products.
CREATE INDEX idx_products_vendor_stock_featured_created
  ON products (vendor_id, in_stock, is_featured, created_at);

CREATE INDEX idx_products_vendor_created
  ON products (vendor_id, created_at);
