-- Migration: Add RFP predictions fields to grant_records
-- This stores predicted RFP opportunities for each grant

ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS predicted_rfps JSONB DEFAULT '[]';
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS rfp_forecast_summary TEXT;
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS rfp_forecast_confidence VARCHAR(10) DEFAULT 'low';
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS total_predicted_rfp_value_min NUMERIC(15,2) DEFAULT 0;
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS total_predicted_rfp_value_max NUMERIC(15,2) DEFAULT 0;
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS predicted_rfp_count INTEGER DEFAULT 0;

-- Add index for efficient filtering of grants with predictions
CREATE INDEX IF NOT EXISTS idx_grant_records_predicted_rfp_count ON grant_records(predicted_rfp_count DESC) WHERE predicted_rfp_count > 0;
CREATE INDEX IF NOT EXISTS idx_grant_records_rfp_forecast_confidence ON grant_records(rfp_forecast_confidence);

COMMENT ON COLUMN grant_records.predicted_rfps IS 'JSONB array of predicted RFP opportunities with type, value ranges, timelines';
COMMENT ON COLUMN grant_records.rfp_forecast_summary IS 'Human-readable summary of RFP predictions';
COMMENT ON COLUMN grant_records.rfp_forecast_confidence IS 'Confidence in the RFP forecast (high, medium, low)';
COMMENT ON COLUMN grant_records.total_predicted_rfp_value_min IS 'Total minimum estimated value of all predicted RFPs';
COMMENT ON COLUMN grant_records.total_predicted_rfp_value_max IS 'Total maximum estimated value of all predicted RFPs';
COMMENT ON COLUMN grant_records.predicted_rfp_count IS 'Number of predicted RFP opportunities';
