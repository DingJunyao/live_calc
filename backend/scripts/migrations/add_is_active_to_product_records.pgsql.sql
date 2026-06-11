-- PostgreSQL migration: add is_active column to product_records
-- Run: psql -U username -d livecalc -f scripts/migrations/add_is_active_to_product_records.pgsql.sql

ALTER TABLE product_records ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Update existing records to be active
UPDATE product_records SET is_active = TRUE WHERE is_active IS NULL;
