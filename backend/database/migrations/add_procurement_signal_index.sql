-- Add missing index on procurement_signal_score for performance
-- This index enables fast filtering and sorting by procurement signal score

CREATE INDEX IF NOT EXISTS idx_grant_records_procurement_signal_score 
ON grant_records(procurement_signal_score DESC);

COMMENT ON INDEX idx_grant_records_procurement_signal_score IS 
'Index for filtering and sorting grants by procurement signal score (0-100)';
