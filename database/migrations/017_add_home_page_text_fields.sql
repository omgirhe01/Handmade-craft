-- Migration 017: Add home page editable text fields to vendors table
-- This allows store owners to edit all home page text sections from Store Settings
-- NOTE: TEXT columns cannot have DEFAULT values in MySQL, so we omit DEFAULT for them.
-- The application handles defaults via Jinja2 template "or" fallback operator.

ALTER TABLE vendors
ADD COLUMN hero_heading VARCHAR(200) DEFAULT '' AFTER about_text,
ADD COLUMN hero_description LONGTEXT NULL AFTER hero_heading,
ADD COLUMN perk1_title VARCHAR(100) DEFAULT 'Handpicked & Curated' AFTER hero_description,
ADD COLUMN perk1_desc VARCHAR(200) DEFAULT 'Every hamper put together with love' AFTER perk1_title,
ADD COLUMN perk2_title VARCHAR(100) DEFAULT 'Custom Orders' AFTER perk1_desc,
ADD COLUMN perk2_desc VARCHAR(200) DEFAULT 'Get your own unique designs' AFTER perk2_title,
ADD COLUMN perk3_title VARCHAR(100) DEFAULT 'Premium Quality' AFTER perk2_desc,
ADD COLUMN perk3_desc VARCHAR(200) DEFAULT 'Best quality materials' AFTER perk3_title,
ADD COLUMN perk4_title VARCHAR(100) DEFAULT 'On Time Delivery' AFTER perk3_desc,
ADD COLUMN perk4_desc VARCHAR(200) DEFAULT 'Timely delivery for every order' AFTER perk4_title,
ADD COLUMN bestsellers_heading VARCHAR(150) DEFAULT 'Our Best Sellers' AFTER perk4_desc,
ADD COLUMN bestsellers_desc VARCHAR(300) DEFAULT 'Handpicked favourites, loved by our customers.' AFTER bestsellers_heading,
ADD COLUMN story_heading VARCHAR(200) DEFAULT 'Every Hamper, Curated With Care' AFTER bestsellers_desc,
ADD COLUMN story_description LONGTEXT NULL AFTER story_heading,
ADD COLUMN testimonials_heading VARCHAR(150) DEFAULT 'What Our Customers Say' AFTER story_description,
ADD COLUMN testimonials_desc VARCHAR(300) DEFAULT 'Real feedback from real customers.' AFTER testimonials_heading,
ADD COLUMN custom_order_heading VARCHAR(150) DEFAULT 'Looking for something special?' AFTER testimonials_desc,
ADD COLUMN custom_order_desc LONGTEXT NULL AFTER custom_order_heading;
