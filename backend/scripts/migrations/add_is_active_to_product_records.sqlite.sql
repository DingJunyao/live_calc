-- SQLite migration: add is_active column to product_records
-- Run: sqlite3 data/livecalc.db < scripts/migrations/add_is_active_to_product_records.sqlite.sql

ALTER TABLE product_records ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1;

-- Update existing records to be active
UPDATE product_records SET is_active = 1 WHERE is_active IS NULL;
