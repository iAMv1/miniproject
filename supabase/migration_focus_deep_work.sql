-- MIGRATION: focus deep-work metric (run in Supabase SQL Editor)
-- Fixes: getFocusState reads deep_work_minutes, column never existed →
-- silent 0. Writers (browser collector + desktop agent) now populate it.

ALTER TABLE focus_snapshots ADD COLUMN IF NOT EXISTS deep_work_minutes real NOT NULL DEFAULT 0;
