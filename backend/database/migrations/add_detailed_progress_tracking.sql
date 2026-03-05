-- Migration: Add detailed progress tracking fields to pipeline_runs
-- This adds fields to track new vs existing records, records with issues, etc.

ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS records_found integer DEFAULT 0;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS records_new integer DEFAULT 0;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS records_existing integer DEFAULT 0;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS records_with_issues integer DEFAULT 0;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS records_deduplicated integer DEFAULT 0;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS records_enriched integer DEFAULT 0;

-- Add comments for documentation
COMMENT ON COLUMN pipeline_runs.records_found IS 'Total records discovered from source';
COMMENT ON COLUMN pipeline_runs.records_new IS 'New records added to database';
COMMENT ON COLUMN pipeline_runs.records_existing IS 'Records that already existed (deduplicated)';
COMMENT ON COLUMN pipeline_runs.records_with_issues IS 'Records with quality issues but not quarantined';
COMMENT ON COLUMN pipeline_runs.records_deduplicated IS 'Records skipped due to deduplication';
COMMENT ON COLUMN pipeline_runs.records_enriched IS 'Existing records that were updated with new data';
