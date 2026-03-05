-- Data Quality Monitoring Queries
-- Run these regularly to monitor data quality

-- ============================================================================
-- 1. DATA COMPLETENESS CHECKS
-- ============================================================================

-- Field completeness by source
SELECT 
  source,
  COUNT(*) as total_grants,
  ROUND(100.0 * COUNT(CASE WHEN recipient_name IS NOT NULL AND recipient_name != '' THEN 1 END) / COUNT(*), 2) as recipient_completeness,
  ROUND(100.0 * COUNT(CASE WHEN issuer_canonical IS NOT NULL AND issuer_canonical != 'Unknown' THEN 1 END) / COUNT(*), 2) as issuer_completeness,
  ROUND(100.0 * COUNT(CASE WHEN amount_cad IS NOT NULL THEN 1 END) / COUNT(*), 2) as amount_completeness,
  ROUND(100.0 * COUNT(CASE WHEN award_date IS NOT NULL THEN 1 END) / COUNT(*), 2) as date_completeness,
  ROUND(100.0 * COUNT(CASE WHEN description IS NOT NULL AND description != '' THEN 1 END) / COUNT(*), 2) as description_completeness
FROM grant_records
GROUP BY source
ORDER BY total_grants DESC;

-- NULL rate analysis
SELECT 
  'recipient_name' as field,
  COUNT(*) as total,
  COUNT(CASE WHEN recipient_name IS NULL OR recipient_name = '' THEN 1 END) as null_count,
  ROUND(100.0 * COUNT(CASE WHEN recipient_name IS NULL OR recipient_name = '' THEN 1 END) / COUNT(*), 2) as null_percentage
FROM grant_records
UNION ALL
SELECT 
  'issuer_canonical' as field,
  COUNT(*) as total,
  COUNT(CASE WHEN issuer_canonical IS NULL OR issuer_canonical = 'Unknown' THEN 1 END) as null_count,
  ROUND(100.0 * COUNT(CASE WHEN issuer_canonical IS NULL OR issuer_canonical = 'Unknown' THEN 1 END) / COUNT(*), 2) as null_percentage
FROM grant_records
UNION ALL
SELECT 
  'amount_cad' as field,
  COUNT(*) as total,
  COUNT(CASE WHEN amount_cad IS NULL THEN 1 END) as null_count,
  ROUND(100.0 * COUNT(CASE WHEN amount_cad IS NULL THEN 1 END) / COUNT(*), 2) as null_percentage
FROM grant_records
UNION ALL
SELECT 
  'award_date' as field,
  COUNT(*) as total,
  COUNT(CASE WHEN award_date IS NULL THEN 1 END) as null_count,
  ROUND(100.0 * COUNT(CASE WHEN award_date IS NULL THEN 1 END) / COUNT(*), 2) as null_percentage
FROM grant_records
ORDER BY null_percentage DESC;

-- ============================================================================
-- 2. CLASSIFICATION & SCORING COVERAGE
-- ============================================================================

-- Classification coverage by source
SELECT 
  source,
  COUNT(*) as total,
  COUNT(CASE WHEN funding_theme IS NOT NULL THEN 1 END) as classified,
  COUNT(CASE WHEN funding_theme IS NULL THEN 1 END) as unclassified,
  COUNT(CASE WHEN procurement_signal_category IS NOT NULL THEN 1 END) as scored,
  COUNT(CASE WHEN procurement_signal_category IS NULL THEN 1 END) as unscored,
  ROUND(100.0 * COUNT(CASE WHEN funding_theme IS NOT NULL THEN 1 END) / COUNT(*), 2) as classification_rate,
  ROUND(100.0 * COUNT(CASE WHEN procurement_signal_category IS NOT NULL THEN 1 END) / COUNT(*), 2) as scoring_rate
FROM grant_records
GROUP BY source
ORDER BY total DESC;

-- Unclassified grants breakdown
SELECT 
  source,
  COUNT(*) as unclassified_count,
  COUNT(CASE WHEN dedup_hash IS NOT NULL THEN 1 END) as cleaned_but_unclassified,
  COUNT(CASE WHEN procurement_signal_category IS NULL THEN 1 END) as unscored
FROM grant_records
WHERE funding_theme IS NULL
GROUP BY source;

-- ============================================================================
-- 3. DATA QUALITY FLAGS
-- ============================================================================

-- Quality flag frequency
SELECT 
  jsonb_array_elements_text(quality_flags) as flag,
  COUNT(*) as frequency,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM grant_records WHERE quality_flags IS NOT NULL AND jsonb_array_length(quality_flags) > 0), 2) as percentage
FROM grant_records
WHERE quality_flags IS NOT NULL AND jsonb_array_length(quality_flags) > 0
GROUP BY flag
ORDER BY frequency DESC;

-- Department matching success rate
SELECT 
  source,
  COUNT(*) as total,
  COUNT(CASE WHEN quality_flags::text LIKE '%unknown_department%' THEN 1 END) as unknown_dept,
  COUNT(CASE WHEN quality_flags::text LIKE '%rule_department_match%' THEN 1 END) as matched_dept,
  ROUND(100.0 * COUNT(CASE WHEN quality_flags::text LIKE '%rule_department_match%' THEN 1 END) / COUNT(*), 2) as match_rate
FROM grant_records
GROUP BY source;

-- ============================================================================
-- 4. QUARANTINE ANALYSIS
-- ============================================================================

-- Quarantine statistics
SELECT 
  quarantine_reason,
  COUNT(*) as count,
  COUNT(DISTINCT source) as sources_affected,
  MIN(created_at) as first_quarantined,
  MAX(created_at) as last_quarantined
FROM quarantine_queue
GROUP BY quarantine_reason
ORDER BY count DESC;

-- Quarantine rate by source
SELECT 
  source,
  COUNT(*) as total_grants,
  (SELECT COUNT(*) FROM quarantine_queue WHERE quarantine_queue.source = grant_records.source) as quarantined,
  ROUND(100.0 * (SELECT COUNT(*) FROM quarantine_queue WHERE quarantine_queue.source = grant_records.source) / COUNT(*), 2) as quarantine_rate
FROM grant_records
GROUP BY source;

-- ============================================================================
-- 5. PROCUREMENT SIGNAL DISTRIBUTION
-- ============================================================================

-- Signal category distribution
SELECT 
  procurement_signal_category,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM grant_records WHERE procurement_signal_category IS NOT NULL), 2) as percentage,
  AVG(procurement_signal_score) as avg_score,
  MIN(procurement_signal_score) as min_score,
  MAX(procurement_signal_score) as max_score
FROM grant_records
WHERE procurement_signal_category IS NOT NULL
GROUP BY procurement_signal_category
ORDER BY 
  CASE procurement_signal_category
    WHEN 'high' THEN 1
    WHEN 'medium' THEN 2
    WHEN 'low' THEN 3
    WHEN 'noise' THEN 4
  END;

-- Signal strength distribution
SELECT 
  signal_strength,
  COUNT(*) as signal_count,
  AVG(grant_count) as avg_grants_per_signal,
  AVG(total_funding_cad) as avg_funding,
  SUM(total_funding_cad) as total_funding
FROM procurement_signals
WHERE is_active = true
GROUP BY signal_strength
ORDER BY 
  CASE signal_strength
    WHEN 'strong' THEN 1
    WHEN 'moderate' THEN 2
    WHEN 'weak' THEN 3
  END;

-- ============================================================================
-- 6. PIPELINE PERFORMANCE
-- ============================================================================

-- Pipeline run statistics (last 30 days)
SELECT 
  COUNT(*) as total_runs,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
  COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
  ROUND(100.0 * COUNT(CASE WHEN status = 'completed' THEN 1 END) / COUNT(*), 2) as success_rate,
  AVG(records_fetched) as avg_fetched,
  AVG(records_cleaned) as avg_cleaned,
  AVG(records_classified) as avg_classified
FROM pipeline_runs
WHERE started_at >= NOW() - INTERVAL '30 days';

-- Recent pipeline runs
SELECT 
  id,
  sources,
  started_at,
  completed_at,
  status,
  records_found,
  records_new,
  records_existing,
  records_cleaned,
  records_classified,
  error_message
FROM pipeline_runs
WHERE started_at >= NOW() - INTERVAL '7 days'
ORDER BY started_at DESC
LIMIT 10;

-- ============================================================================
-- 7. DATA CONSISTENCY CHECKS
-- ============================================================================

-- Duplicate detection
SELECT 
  dedup_hash,
  COUNT(*) as duplicate_count,
  array_agg(DISTINCT source) as sources,
  array_agg(id) as grant_ids
FROM grant_records
WHERE dedup_hash IS NOT NULL
GROUP BY dedup_hash
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- Data freshness
SELECT 
  source,
  COUNT(*) as total,
  MIN(created_at) as oldest_record,
  MAX(created_at) as newest_record,
  MAX(updated_at) as last_updated,
  AVG(EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400) as avg_age_days
FROM grant_records
GROUP BY source;

-- ============================================================================
-- 8. BUSINESS ALIGNMENT METRICS
-- ============================================================================

-- Business relevance vs procurement signal alignment
SELECT 
  business_relevance,
  procurement_signal_category,
  COUNT(*) as count,
  AVG(business_relevance_score * 100) as avg_business_score,
  AVG(procurement_signal_score) as avg_procurement_score,
  ABS(AVG(business_relevance_score * 100) - AVG(procurement_signal_score)) as score_difference
FROM grant_records
WHERE business_relevance IS NOT NULL 
  AND procurement_signal_category IS NOT NULL
  AND business_relevance != 'unknown'
GROUP BY business_relevance, procurement_signal_category
ORDER BY count DESC;

-- High signal grants analysis
SELECT 
  procurement_signal_category,
  COUNT(*) as count,
  AVG(amount_cad) as avg_amount,
  SUM(amount_cad) as total_amount,
  COUNT(DISTINCT funding_theme) as unique_themes,
  COUNT(DISTINCT region) as unique_regions
FROM grant_records
WHERE procurement_signal_category IN ('high', 'medium')
GROUP BY procurement_signal_category;
