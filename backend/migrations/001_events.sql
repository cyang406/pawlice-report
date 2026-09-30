-- One-time migration for an existing Pawlice Report MySQL database.
-- Run this before starting the V2 backend. Do not run it twice.
-- Existing rows receive the INCIDENT default. IDs, dates, URLs, and images are unchanged.
ALTER TABLE incidents
  ADD COLUMN event_type VARCHAR(20) NOT NULL DEFAULT 'INCIDENT',
  MODIFY COLUMN severity INTEGER NULL;
