# Data Quality Review Report
**Generated:** 2026-03-05  
**Database:** Supabase (Publicus Signal Engine)  
**Total Grants:** 5,192

## Executive Summary

This comprehensive review assessed data quality across 5 dimensions: completeness, classification coverage, data accuracy, business alignment, and best practices. The review identified **4 critical issues** requiring immediate attention, with the most severe being that **97.7% of grants are unclassified**, rendering the procurement signal system largely ineffective.

### Overall Health Score: 45/100

- ✅ **Data Completeness:** 100% (Excellent)
- ❌ **Classification Coverage:** 2.3% (Critical)
- ⚠️ **Data Accuracy:** 63% (Needs Improvement)
- ⚠️ **Business Alignment:** 40% (Poor)
- ✅ **Schema Design:** 85% (Good)

---

## 1. Data Completeness Audit

### Results: ✅ EXCELLENT (100%)

**Critical Fields:**
- ✅ Recipient Name: 100% complete (0% NULL)
- ✅ Issuer Canonical: 100% complete (0% NULL)
- ✅ Amount CAD: 100% complete (0% NULL)
- ✅ Award Date: 100% complete (0% NULL)
- ✅ Description: 100% complete (0% NULL)

**Optional Fields:**
- Program Name: 97.6% complete (122 missing)
- Region: 98.2% complete (94 missing)
- Recipient Type: 97.5% complete (130 missing)

**Data Type Validation:**
- ✅ Amounts: All valid (no negative, no zero, max $263M)
- ⚠️ Dates: 14 future dates detected (2027-01-01)
- ✅ No constraint violations detected

**Verdict:** Data completeness is excellent. All critical fields are populated. Minor issues with future dates need investigation.

---

## 2. Classification & Scoring Coverage Analysis

### Results: ❌ CRITICAL (2.3%)

**The Problem:**
- **5,073 grants (97.7%) from `open_canada` are completely unclassified and unscored**
- Only 119 CSV grants (2.3%) are fully processed
- **0 grants have procurement signal scores from open_canada source**

**Root Cause Analysis:**

1. **Pipeline Issue:** Recent pipeline runs show:
   - `records_fetched: 5000` ✅
   - `records_cleaned: 0` ❌ (Should be ~5000)
   - `records_classified: 0` ❌
   - `records_existing: 4909` (all deduplicated)

2. **Classification Not Triggered:**
   - `_classify_grants()` is called but queries database directly
   - Method expects `funding_theme IS NULL` grants
   - All 5,073 grants have `funding_theme IS NULL`
   - But classification is not running

3. **Why Classification Fails:**
   - When all grants already exist (`records_new: 0`), the `cleaned_grants` list passed to `_classify_grants()` may be empty
   - However, `_classify_grants()` queries DB directly, so this shouldn't matter
   - **Actual issue:** Classification may not be running because `records_cleaned: 0` is being interpreted as "nothing to classify"

**Impact:**
- Procurement signals are based on only 2.3% of available data
- 84 signals generated from 119 grants (should be from 5,000+ grants)
- Signals are incomplete and potentially misleading
- Business value is severely compromised

**Recommendation:** **URGENT** - Fix classification pipeline to process all unclassified grants regardless of whether they're new or existing.

---

## 3. Data Quality Flag Analysis

### Results: ⚠️ NEEDS IMPROVEMENT (63%)

**Quality Flag Distribution:**
- `unknown_department`: 1,915 grants (94.1% of flagged grants)
- `rule_department_match`: 119 grants (5.8%)
- `future_date`: 11 grants (0.5%)

**Department Matching Issues:**
- 36.9% of open_canada grants have "unknown_department" flag
- Only 2.3% have successful department matches
- This affects signal clustering and issuer normalization

**Quarantine Analysis:**
- 524 records quarantined (all from open_canada)
- All with reason: "unknown"
- Quarantine rate: 10.3% of open_canada grants
- No pipeline_run_id linked (orphaned quarantine records)

**Issues:**
1. **Department Matching:** The `DEPT_CANONICAL` mapping in `cleaner.py` is too limited (only ~20 departments). Open Canada has 43 unique issuers, but most aren't in the mapping.
2. **Quarantine Tracking:** Quarantine records have no `pipeline_run_id`, making it impossible to trace when/why they were quarantined.
3. **Future Dates:** 14 grants have dates in 2027, indicating data quality issues in source.

**Recommendation:** Expand department mapping and improve quarantine tracking.

---

## 4. Business Alignment Assessment

### Results: ⚠️ POOR (40%)

**Procurement Signal Distribution (from 119 CSV grants only):**
- High Signal: 3 grants (2.5%) ✅
- Medium Signal: 6 grants (5.0%) ✅
- Low Signal: 5 grants (4.2%)
- Noise: 105 grants (88.2%)

**Signal Strength (84 signals generated):**
- Strong: 25 signals (29.8%) - $1.13B total funding
- Moderate: 46 signals (54.8%) - $111M total funding
- Weak: 13 signals (15.5%) - $4.2M total funding

**Scoring System Mismatch:**
- 21 grants marked "high" business relevance but "noise" procurement signal
- 31 grants marked "medium" business relevance but "noise" procurement signal
- **Score difference:** Business relevance and procurement signal scores are not aligned
- Average difference: 30-80 points between systems

**Issues:**
1. **Incomplete Signal Generation:** Signals based on only 119 grants instead of 5,000+
2. **Scoring Confusion:** Two different scoring systems (business_relevance vs procurement_signal) produce conflicting results
3. **Low Signal Rate:** Only 7.5% of grants have medium/high procurement signals (expected: 8-12%)

**Recommendation:** 
- Unify scoring systems or clearly document when to use each
- Re-generate signals after fixing classification
- Validate that 6-dimension model is working correctly

---

## 5. Schema & Best Practices Review

### Results: ✅ GOOD (85%)

**Indexes:**
- ✅ 19 indexes on `grant_records` (comprehensive coverage)
- ✅ Indexes on: source, funding_theme, procurement_signal_category, region, dates
- ✅ Composite index for signal detection: `(funding_theme, procurement_category, region)`
- ✅ Partial indexes for performance: `WHERE is_quarantined = false`
- ⚠️ Missing: Index on `procurement_signal_score` (for sorting/filtering)

**Constraints:**
- ✅ Check constraints on: recipient_type, description_quality, business_relevance
- ✅ Unique constraint on dedup_hash (prevents duplicates)
- ✅ Foreign key: quarantine_queue → pipeline_runs
- ✅ No constraint violations detected

**RLS Policies:**
- ✅ Public read access on grant_records and procurement_signals
- ✅ Quarantine queue properly restricted
- ✅ Policies are appropriate for public data

**Schema Issues:**
1. **Missing Index:** `procurement_signal_score` should have an index for filtering/sorting
2. **JSONB Usage:** Appropriate use of JSONB for `quality_flags`, `raw_data`, `procurement_signal_reasons`
3. **Normalization:** Good normalization - no redundant data

**Recommendation:** Add index on `procurement_signal_score` for performance.

---

## 6. Pipeline Performance & Reliability

### Results: ⚠️ NEEDS IMPROVEMENT (55%)

**Pipeline Run Statistics (Last 30 Days):**
- Total Runs: 49
- Completed: 27 (55.1% success rate)
- Failed: 14 (28.6% failure rate)
- Running: 8 (16.3% stuck/running)
- Average Duration: -13,219 seconds (negative = data issue)

**Issues:**
1. **Low Success Rate:** Only 55% of runs complete successfully
2. **High Failure Rate:** 28.6% of runs fail
3. **Stuck Runs:** 8 runs still in "running" status (may be stuck)
4. **Duration Calculation:** Negative duration indicates `completed_at < started_at` (timezone or data issue)

**Processing Metrics:**
- Average Fetched: 1,740 grants
- Average Cleaned: 106 grants (should be ~1,740)
- Average Classified: 2.5 grants (should be ~1,740)
- Average Quarantined: 10.7 grants

**Recent Run Pattern:**
- All recent runs show `records_cleaned: 0` even when `records_found: 5000`
- This indicates a bug in progress tracking or cleaning logic

**Recommendation:** 
- Investigate why `records_cleaned` is 0 when grants exist
- Fix duration calculation (timezone issue)
- Investigate stuck "running" runs

---

## 7. Data Consistency Checks

### Results: ✅ GOOD (90%)

**Deduplication:**
- ✅ No duplicate `dedup_hash` values found
- ✅ Deduplication is working correctly
- ✅ All 5,192 grants have unique dedup_hash

**Orphaned Records:**
- ✅ No orphaned quarantine records (all have valid structure)
- ⚠️ 524 quarantine records have no `pipeline_run_id` (cannot trace origin)

**Data Freshness:**
- CSV grants: Average age 1.2 days, last updated 2026-03-05
- Open Canada grants: Average age 0.1 days, last updated 2026-03-05
- ✅ Data is very fresh (recently fetched)

**Referential Integrity:**
- ✅ All foreign keys valid
- ✅ No orphaned records detected

**Recommendation:** Link quarantine records to pipeline runs for traceability.

---

## Critical Issues Summary

### 🔴 CRITICAL (Fix Immediately)

1. **97.7% of Grants Unclassified**
   - **Impact:** Procurement signals based on only 2.3% of data
   - **Root Cause:** Classification pipeline not running for existing grants
   - **Fix:** Ensure `_classify_grants()` processes all unclassified grants regardless of new/existing status

2. **Classification Not Running**
   - **Impact:** No grants being classified or scored
   - **Root Cause:** `records_cleaned: 0` when all grants already exist
   - **Fix:** Update progress tracking to count existing grants as "cleaned"

### 🟡 HIGH PRIORITY (Fix Soon)

3. **Department Matching Failure (36.9%)**
   - **Impact:** Poor issuer normalization affects signal clustering
   - **Fix:** Expand `DEPT_CANONICAL` mapping to cover all 43 unique issuers

4. **Scoring System Mismatch**
   - **Impact:** Confusion about which scoring system to trust
   - **Fix:** Unify systems or clearly document usage

5. **Quarantine Tracking Missing**
   - **Impact:** Cannot trace why 524 records were quarantined
   - **Fix:** Link quarantine records to pipeline runs

### 🟢 MEDIUM PRIORITY (Improve)

6. **Future Dates (14 grants)**
   - **Impact:** Data quality concerns
   - **Fix:** Investigate source data or add validation

7. **Missing Index on procurement_signal_score**
   - **Impact:** Performance degradation on filtering/sorting
   - **Fix:** Add index

8. **Pipeline Success Rate (55%)**
   - **Impact:** Unreliable pipeline execution
   - **Fix:** Investigate failures and stuck runs

---

## Recommendations

### Immediate Actions (This Week)

1. **Fix Classification Pipeline**
   - Modify `_classify_grants()` to query and process ALL unclassified grants
   - Ensure it runs even when `records_new: 0`
   - Add logging to track classification progress

2. **Fix Progress Tracking**
   - Update `records_cleaned` to count existing grants that are processed
   - Fix duration calculation (timezone issue)

3. **Run Classification on Existing Grants**
   - Create script to classify all 5,073 unclassified grants
   - Run procurement signal scoring on all grants
   - Re-generate procurement signals

### Short-term (This Month)

4. **Expand Department Mapping**
   - Analyze all 43 unique issuers from open_canada
   - Add mappings to `DEPT_CANONICAL`
   - Reduce "unknown_department" flag rate to <5%

5. **Improve Quarantine Tracking**
   - Link quarantine records to pipeline runs
   - Add detailed failure reasons
   - Create dashboard for quarantine review

6. **Unify Scoring Systems**
   - Decide on single scoring system or clearly document when to use each
   - Align business_relevance and procurement_signal scores
   - Update UI to show consistent scoring

### Long-term (Next Quarter)

7. **Performance Optimization**
   - Add missing indexes
   - Optimize query patterns
   - Monitor pipeline performance

8. **Data Quality Monitoring**
   - Create automated data quality checks
   - Set up alerts for quality degradation
   - Regular data quality reports

---

## Success Metrics

**Current State:**
- Classification Rate: 2.3% ❌ (Target: 90%+)
- Procurement Signal Coverage: 2.3% ❌ (Target: 100%)
- Department Matching: 2.3% ❌ (Target: 95%+)
- Pipeline Success Rate: 55% ⚠️ (Target: 90%+)
- Data Completeness: 100% ✅ (Target: 95%+)

**Target State (After Fixes):**
- Classification Rate: 90%+
- Procurement Signal Coverage: 100%
- Department Matching: 95%+
- Pipeline Success Rate: 90%+
- Data Completeness: 100% (maintain)

---

## Conclusion

The database has **excellent data completeness** but **critical gaps in classification and scoring**. The primary issue is that 97.7% of grants are unclassified, which severely limits the system's ability to generate meaningful procurement signals. 

**Priority:** Fix the classification pipeline immediately to process all 5,073 unclassified grants. This will unlock the full value of the data and enable accurate procurement signal generation.

The schema design is solid, indexes are well-placed, and data consistency is good. The main improvements needed are in the pipeline execution and classification coverage.
