-- Add game_data column to modules table.
-- Run this if you already ran modules_table.sql and need the new column.

ALTER TABLE modules ADD COLUMN IF NOT EXISTS game_data jsonb NOT NULL DEFAULT '{}';
