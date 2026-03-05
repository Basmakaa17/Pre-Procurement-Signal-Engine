-- Complete Schema for Publicus Signal Engine
-- Run this in the Supabase SQL Editor to set up all required tables

-- ============================================================================
-- TABLE: grant_records
-- Stores scraped grant records from various sources
-- ============================================================================
DROP TABLE IF EXISTS grant_records CASCADE;
CREATE TABLE grant_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source varchar(50) NOT NULL,
    source_record_id varchar(255),
    issuer_canonical varchar(255), -- Made nullable (enforced at application level)
    issuer_raw varchar(255),
    recipient_name varchar(500), -- Made nullable (enforced at application level)
    recipient_name_normalized varchar(500),
    recipient_type varchar(50),
    amount_cad numeric(15,2),
    amount_unknown boolean DEFAULT false,
    award_date date,
    fiscal_year varchar(10),
    region varchar(100),
    description text,
    program_name varchar(500),
    program_name_normalized varchar(500),
    description_quality varchar(20) DEFAULT 'unknown',
    funding_theme varchar(100),
    procurement_category varchar(100),
    sector_tags text[],
    llm_confidence numeric(3,2),
    llm_classified_at timestamptz,
    llm_needs_review boolean DEFAULT false,
    llm_review_reason varchar(255),
    quality_flags jsonb DEFAULT '[]',
    is_quarantined boolean DEFAULT false,
    business_relevance varchar(20) DEFAULT 'unknown',
    business_relevance_score numeric(3,2) DEFAULT 0.5,
    business_relevance_reasons jsonb DEFAULT '[]',
    agreement_type varchar(50),
    procurement_signal_score integer,
    procurement_signal_category varchar(20),
    procurement_signal_reasons jsonb DEFAULT '[]',
    grant_duration_months integer,
    predicted_rfps jsonb DEFAULT '[]',
    rfp_forecast_summary text,
    rfp_forecast_confidence varchar(10) DEFAULT 'low',
    total_predicted_rfp_value_min numeric(15,2) DEFAULT 0,
    total_predicted_rfp_value_max numeric(15,2) DEFAULT 0,
    predicted_rfp_count integer DEFAULT 0,
    dedup_hash varchar(64) UNIQUE,
    raw_data jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    CONSTRAINT chk_recipient_type CHECK (recipient_type IN (
        'municipal_government','provincial_government','federal_government',
        'university','hospital_health','indigenous','nonprofit',
        'private_company','unknown'
    ) OR recipient_type IS NULL),
    CONSTRAINT chk_description_quality CHECK (description_quality IN (
        'good','low','missing','unknown'
    )),
    CONSTRAINT chk_business_relevance CHECK (business_relevance IN (
        'high','medium','low','unknown'
    ))
);

-- ============================================================================
-- TABLE: procurement_signals
-- Aggregated signals derived from grant records
-- ============================================================================
DROP TABLE IF EXISTS procurement_signals CASCADE;
CREATE TABLE procurement_signals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_name varchar(255) NOT NULL,
    funding_theme varchar(100) NOT NULL,
    procurement_category varchar(100) NOT NULL,
    department_cluster varchar(255),
    region varchar(100),
    total_funding_cad numeric(15,2),
    grant_count integer DEFAULT 0,
    earliest_grant_date date,
    latest_grant_date date,
    time_horizon_min_months integer,
    time_horizon_max_months integer,
    confidence_score numeric(3,2),
    signal_strength varchar(20),
    predicted_rfp_window_start date,
    predicted_rfp_window_end date,
    supporting_grant_ids uuid[],
    is_active boolean DEFAULT true,
    momentum_score numeric(5,2),
    momentum_direction varchar(10),
    last_signal_refresh timestamptz,
    recommended_action text,
    why_this_signal text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    CONSTRAINT chk_signal_strength CHECK (signal_strength IN (
        'weak','moderate','strong'
    ) OR signal_strength IS NULL),
    CONSTRAINT chk_momentum_direction CHECK (momentum_direction IN (
        'up','down','stable'
    ) OR momentum_direction IS NULL),
    CONSTRAINT uq_signal_identity UNIQUE (funding_theme, procurement_category, region)
);

-- ============================================================================
-- TABLE: pipeline_runs
-- Tracks pipeline execution history
-- ============================================================================
DROP TABLE IF EXISTS pipeline_runs CASCADE;
CREATE TABLE pipeline_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sources text[] DEFAULT '{}',
    started_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    status varchar(20),
    records_fetched integer DEFAULT 0,
    records_cleaned integer DEFAULT 0,
    records_quarantined integer DEFAULT 0,
    records_classified integer DEFAULT 0,
    error_message text,
    cleaning_report jsonb DEFAULT '{}',
    metadata jsonb DEFAULT '{}'
);

-- ============================================================================
-- TABLE: quarantine_queue
-- Stores records that failed validation or processing
-- ============================================================================
DROP TABLE IF EXISTS quarantine_queue CASCADE;
CREATE TABLE quarantine_queue (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source varchar(50),
    pipeline_run_id uuid REFERENCES pipeline_runs(id),
    quarantine_reason varchar(100) NOT NULL DEFAULT 'unknown',
    raw_data jsonb NOT NULL,
    failure_reasons text[] NOT NULL,
    resolved boolean DEFAULT false,
    resolved_at timestamptz,
    resolved_by varchar(100),
    resolution_notes text,
    created_at timestamptz DEFAULT now()
);

-- ============================================================================
-- TABLE: pipeline_source_metadata
-- Tracks metadata for each data source, including last fetch time
-- ============================================================================
DROP TABLE IF EXISTS pipeline_source_metadata CASCADE;
CREATE TABLE pipeline_source_metadata (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source varchar(100) UNIQUE NOT NULL,
    last_fetch_timestamp timestamptz,
    total_records_fetched integer DEFAULT 0,
    last_run_status varchar(50),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- ============================================================================
-- TABLE: procurement_taxonomy
-- Lookup table for procurement categories and themes
-- ============================================================================
DROP TABLE IF EXISTS procurement_taxonomy CASCADE;
CREATE TABLE procurement_taxonomy (
    id serial PRIMARY KEY,
    grant_theme varchar(100) UNIQUE NOT NULL,
    procurement_category varchar(100) NOT NULL,
    lag_months_min integer NOT NULL,
    lag_months_max integer NOT NULL,
    confidence_base numeric(3,2),
    notes text
);

-- ============================================================================
-- INDEXES
-- ============================================================================
-- grant_records
CREATE INDEX idx_grant_records_source ON grant_records(source);
CREATE INDEX idx_grant_records_funding_theme ON grant_records(funding_theme);
CREATE INDEX idx_grant_records_region ON grant_records(region);
CREATE INDEX idx_grant_records_award_date ON grant_records(award_date);
CREATE INDEX idx_grant_records_dedup_hash ON grant_records(dedup_hash);
CREATE INDEX idx_grant_records_is_quarantined ON grant_records(is_quarantined);
CREATE INDEX idx_grant_records_procurement_category ON grant_records(procurement_category);
CREATE INDEX idx_grant_records_signal_detection ON grant_records(funding_theme, procurement_category, region) WHERE is_quarantined = false;
CREATE INDEX idx_grant_records_llm_confidence ON grant_records(llm_confidence);
CREATE INDEX idx_grant_records_unclassified ON grant_records(llm_classified_at) WHERE llm_classified_at IS NULL;
CREATE INDEX idx_grant_records_business_relevance ON grant_records(business_relevance);
CREATE INDEX idx_grant_records_business_relevance_score ON grant_records(business_relevance_score DESC);
CREATE INDEX idx_grant_records_procurement_signal ON grant_records(procurement_signal_category);
CREATE INDEX idx_grant_records_agreement_type ON grant_records(agreement_type);

-- procurement_signals
CREATE INDEX idx_procurement_signals_funding_theme ON procurement_signals(funding_theme);
CREATE INDEX idx_procurement_signals_region ON procurement_signals(region);
CREATE INDEX idx_procurement_signals_confidence_score ON procurement_signals(confidence_score DESC);
CREATE INDEX idx_procurement_signals_is_active ON procurement_signals(is_active);

-- pipeline_source_metadata
CREATE INDEX idx_pipeline_source_metadata_source ON pipeline_source_metadata(source);

-- ============================================================================
-- SEED DATA
-- ============================================================================
-- Insert default source metadata records
INSERT INTO pipeline_source_metadata (source, last_fetch_timestamp, total_records_fetched, last_run_status)
VALUES 
    ('open_canada', NOW() - INTERVAL '6 hours', 0, 'initialized'),
    ('innovation_canada', NOW() - INTERVAL '6 hours', 0, 'initialized'),
    ('proactive_disclosure', NOW() - INTERVAL '6 hours', 0, 'initialized')
ON CONFLICT (source) DO NOTHING;

-- ============================================================================
-- TRIGGERS
-- ============================================================================
-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to update updated_at on each update
CREATE TRIGGER trg_grant_records_updated_at
  BEFORE UPDATE ON grant_records
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_procurement_signals_updated_at
  BEFORE UPDATE ON procurement_signals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_pipeline_source_metadata_updated_at
  BEFORE UPDATE ON pipeline_source_metadata
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Insert procurement taxonomy seed data
INSERT INTO procurement_taxonomy 
    (grant_theme, procurement_category, lag_months_min, lag_months_max, confidence_base, notes)
VALUES
    ('Cybersecurity Modernization', 'IT Security Consulting', 6, 9, 0.85, 'Municipal and provincial cyber programs consistently lead to security RFPs'),
    ('Digital Transformation', 'Software Development & IT Consulting', 3, 6, 0.90, 'Innovation pilots move to procurement fastest'),
    ('AI & Machine Learning', 'AI/ML Consulting & Development', 3, 8, 0.88, 'Federal AI strategy programs'),
    ('Healthcare Digitization', 'Health IT & EHR Systems', 6, 12, 0.82, 'Health Canada and provincial health authorities'),
    ('Clean Energy Infrastructure', 'Engineering & Environmental Consulting', 12, 18, 0.75, 'Longer lead time due to project complexity'),
    ('Municipal Modernization', 'Cloud & SaaS Procurement', 6, 12, 0.80, 'Smart city and service digitization grants'),
    ('Workforce Development', 'Training & HR Consulting', 3, 9, 0.70, 'Skills programs often lead to workforce consulting RFPs'),
    ('Research & Innovation', 'Research & Advisory Services', 6, 12, 0.72, 'NRC and granting council programs'),
    ('Transportation & Logistics', 'Infrastructure & Systems Integration', 9, 18, 0.76, 'Transport Canada and provincial programs'),
    ('Environmental & Climate', 'Environmental Consulting', 6, 15, 0.74, 'Climate action funds and green programs'),
    ('Indigenous Programs', 'Community & Social Consulting', 6, 12, 0.68, 'ISC and Crown-Indigenous relations programs'),
    ('Defence & Security', 'Defence Consulting & Systems', 6, 12, 0.78, 'DND and public safety programs')
ON CONFLICT (grant_theme) DO NOTHING;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================
-- Enable RLS on sensitive tables
ALTER TABLE grant_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE procurement_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE quarantine_queue ENABLE ROW LEVEL SECURITY;

-- Allow read-only access via anon key (for frontend)
CREATE POLICY "Public read grant_records" ON grant_records
  FOR SELECT USING (true);

CREATE POLICY "Public read procurement_signals" ON procurement_signals
  FOR SELECT USING (true);

-- Quarantine is backend-only — no anon access
CREATE POLICY "No public access quarantine" ON quarantine_queue
  FOR ALL USING (false);