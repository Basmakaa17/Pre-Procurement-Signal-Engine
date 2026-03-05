-- Migration: Add business relevance fields to grant_records
-- This helps filter grants based on their likelihood to lead to business opportunities/RFPs

-- Add business_relevance column with constraint
ALTER TABLE grant_records ADD COLUMN business_relevance varchar(20) DEFAULT 'unknown';
ALTER TABLE grant_records ADD CONSTRAINT chk_business_relevance CHECK (
    business_relevance IN ('high', 'medium', 'low', 'unknown')
);

-- Add business_relevance_score column (0.0 to 1.0)
ALTER TABLE grant_records ADD COLUMN business_relevance_score numeric(3,2) DEFAULT 0.5;

-- Add business_relevance_reasons column to store matching reasons
ALTER TABLE grant_records ADD COLUMN business_relevance_reasons jsonb DEFAULT '[]';

-- Add index for efficient filtering
CREATE INDEX idx_grant_records_business_relevance ON grant_records(business_relevance);
CREATE INDEX idx_grant_records_business_relevance_score ON grant_records(business_relevance_score DESC);

-- Update the complete schema for future installations
COMMENT ON COLUMN grant_records.business_relevance IS 'Likelihood to lead to business opportunities (high, medium, low, unknown)';
COMMENT ON COLUMN grant_records.business_relevance_score IS 'Numerical score (0.0-1.0) for business relevance';
COMMENT ON COLUMN grant_records.business_relevance_reasons IS 'Reasons for business relevance classification';