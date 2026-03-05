-- Add procurement signal columns for the 6-dimension RFP eligibility model
-- Run this in the Supabase SQL Editor

-- Add agreement_type column
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS agreement_type varchar(50);

-- Add procurement signal score (0-100)
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS procurement_signal_score integer;

-- Add procurement signal category
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS procurement_signal_category varchar(20);

-- Add procurement signal reasons
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS procurement_signal_reasons jsonb DEFAULT '[]';

-- Add grant duration in months
ALTER TABLE grant_records ADD COLUMN IF NOT EXISTS grant_duration_months integer;

-- Add indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_grant_records_procurement_signal ON grant_records(procurement_signal_category);
CREATE INDEX IF NOT EXISTS idx_grant_records_agreement_type ON grant_records(agreement_type);

-- Add comments
COMMENT ON COLUMN grant_records.agreement_type IS 'Type of agreement (contribution, grant, other transfer payment)';
COMMENT ON COLUMN grant_records.procurement_signal_score IS 'Score (0-100) indicating likelihood of generating RFPs based on 6-dimension model';
COMMENT ON COLUMN grant_records.procurement_signal_category IS 'Signal category: high (>=60), medium (40-59), low (20-39), noise (<20)';
COMMENT ON COLUMN grant_records.procurement_signal_reasons IS 'Reasons/factors contributing to the procurement signal score';
COMMENT ON COLUMN grant_records.grant_duration_months IS 'Duration of grant in months (end_date - start_date)';
