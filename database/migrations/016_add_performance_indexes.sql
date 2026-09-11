-- Migration 016: Add missing indexes that were slowing the site down.
--
-- orders.phone / custom_orders.mobile were never indexed, even though
-- every "Find My Orders" lookup filters by exactly that column -- on a
-- table with many rows this was a full table scan every single search.
-- status/created_at are added too since the dashboards filter/sort by them
-- constantly (Pending count, recent orders, etc).
CREATE INDEX idx_orders_phone ON orders (phone);
CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_orders_created_at ON orders (created_at);

CREATE INDEX idx_custom_orders_mobile ON custom_orders (mobile);
CREATE INDEX idx_custom_orders_status ON custom_orders (status);
CREATE INDEX idx_custom_orders_created_at ON custom_orders (created_at);
