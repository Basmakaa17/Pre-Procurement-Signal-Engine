# Data Quality Recommendations
**Priority Order:** Based on impact and effort

## Immediate Actions (This Week)

### 1. Fix Classification Pipeline ⚠️ CRITICAL
**Priority:** P0 - Blocking  
**Effort:** 2-4 hours  
**Impact:** Unlocks 97.7% of unclassified data

**Problem:**
- 5,073 grants are unclassified because classification doesn't run for existing grants
- `records_cleaned: 0` when all grants already exist prevents classification

**Solution:**
1. Modify `_classify_grants()` in `orchestrator.py` to:
   - Query ALL unclassified grants from database (not just from `cleaned_grants` parameter)
   - Process grants regardless of whether they're new or existing
   - Add batch processing with progress updates

2. Fix progress tracking:
   - Update `records_cleaned` to count existing grants that are processed
   - Set `records_cleaned = records_new + records_existing` (total processed)

3. Create classification script:
   - Script to classify all 5,073 unclassified grants
   - Run procurement signal scoring
   - Re-generate procurement signals

**Files:**
- `backend/app/pipeline/orchestrator.py` - `_classify_grants()` method
- `backend/app/pipeline/orchestrator.py` - Progress tracking logic
- `backend/scripts/classify_all_grants.py` - New script

**Success Criteria:**
- 90%+ classification rate
- All grants have procurement signal scores
- Signals regenerated with full dataset

---

### 2. Expand Department Mapping ⚠️ HIGH
**Priority:** P1 - High  
**Effort:** 4-6 hours  
**Impact:** Reduces "unknown_department" from 36.9% to <5%

**Problem:**
- Only ~20 departments in `DEPT_CANONICAL` mapping
- 43 unique issuers in database
- 1,915 grants flagged as "unknown_department"

**Solution:**
1. Analyze all unique issuers:
   ```sql
   SELECT DISTINCT issuer_canonical, COUNT(*) 
   FROM grant_records 
   WHERE source = 'open_canada' 
   GROUP BY issuer_canonical 
   ORDER BY COUNT(*) DESC;
   ```

2. Expand `DEPT_CANONICAL` mapping:
   - Add all missing departments
   - Include common abbreviations and French names
   - Add fuzzy matching patterns

3. Improve matching algorithm:
   - Add fuzzy string matching for partial matches
   - Handle bilingual department names
   - Add fallback matching strategies

**Files:**
- `backend/app/pipeline/cleaner.py` - `DEPT_CANONICAL` dictionary
- `backend/app/pipeline/cleaner.py` - `canonicalize_department()` function

**Success Criteria:**
- <5% of grants with "unknown_department" flag
- 95%+ department matching success rate

---

### 3. Unify Scoring Systems ⚠️ HIGH
**Priority:** P1 - High  
**Effort:** 2-3 hours  
**Impact:** Eliminates confusion, improves consistency

**Problem:**
- Two scoring systems: `business_relevance` and `procurement_signal`
- 105 grants have conflicting scores
- No clear documentation on when to use each

**Solution:**
**Option A: Use Procurement Signal Only (Recommended)**
- Remove `business_relevance` scoring
- Use `procurement_signal_category` as primary filter
- Update UI to show only procurement signal

**Option B: Align Both Systems**
- Make `business_relevance` a simplified version of `procurement_signal`
- Use same thresholds and criteria
- Document when to use each

**Option C: Keep Separate, Document Clearly**
- Document that `procurement_signal` is the primary system
- `business_relevance` is legacy/deprecated
- Update UI to deprecate business_relevance

**Recommendation:** Option A - Use procurement signal only, as it's more sophisticated and based on 6-dimension model.

**Files:**
- `backend/app/intelligence/procurement_signal_score.py`
- `backend/app/intelligence/business_relevance_filter.py` (deprecate)
- Frontend components showing scores
- API endpoints

**Success Criteria:**
- Single scoring system in use
- No conflicting scores
- Clear documentation

---

### 4. Improve Quarantine Tracking ⚠️ HIGH
**Priority:** P1 - High  
**Effort:** 2-3 hours  
**Impact:** Enables traceability and debugging

**Problem:**
- 524 quarantine records have no `pipeline_run_id`
- Cannot trace when/why records were quarantined
- Quarantine reason is "unknown" for all

**Solution:**
1. Link quarantine to pipeline runs:
   - Pass `pipeline_run_id` to quarantine creation
   - Store in `quarantine_queue.pipeline_run_id`
   - Add foreign key constraint

2. Capture detailed failure reasons:
   - Store full quality flags array
   - Add timestamp of quarantine
   - Include grant metadata

3. Create quarantine dashboard:
   - View quarantined records by run
   - Filter by reason
   - Bulk review/resolve

**Files:**
- `backend/app/pipeline/orchestrator.py` - Quarantine creation
- `backend/app/pipeline/cleaner.py` - Quarantine logic
- `backend/database/migrations/add_quarantine_tracking.sql` - Migration

**Success Criteria:**
- All quarantine records linked to pipeline runs
- Detailed failure reasons captured
- Dashboard available for review

---

## Short-term Improvements (This Month)

### 5. Add Missing Indexes
**Priority:** P2 - Medium  
**Effort:** 15 minutes  
**Impact:** Improves query performance

**Missing Index:**
```sql
CREATE INDEX idx_grant_records_procurement_signal_score 
ON grant_records(procurement_signal_score DESC);
```

**Files:**
- `backend/database/migrations/add_procurement_signal_index.sql`

---

### 6. Fix Future Dates Validation
**Priority:** P2 - Medium  
**Effort:** 1 hour  
**Impact:** Improves data quality

**Solution:**
- Add validation to reject dates > 1 year in future
- Flag for manual review
- Investigate source data quality

**Files:**
- `backend/app/pipeline/cleaner.py` - `clean_date()` function

---

### 7. Improve Pipeline Reliability
**Priority:** P2 - Medium  
**Effort:** 4-6 hours  
**Impact:** Increases success rate from 55% to 90%+

**Solution:**
1. Investigate failures:
   - Analyze error messages from failed runs
   - Identify common failure patterns
   - Add retry logic for transient failures

2. Fix stuck runs:
   - Identify why 8 runs are stuck in "running"
   - Add timeout mechanism
   - Auto-mark as failed after timeout

3. Improve error handling:
   - Better error messages
   - Graceful degradation
   - Partial success handling

**Files:**
- `backend/app/pipeline/orchestrator.py` - Error handling
- `backend/app/api/pipeline.py` - Pipeline API

---

## Long-term Enhancements (Next Quarter)

### 8. Automated Data Quality Monitoring
**Priority:** P3 - Low  
**Effort:** 8-12 hours  
**Impact:** Proactive quality management

**Solution:**
- Create scheduled jobs to run quality checks
- Set up alerts for quality degradation
- Generate weekly quality reports
- Dashboard for quality metrics

---

### 9. Performance Optimization
**Priority:** P3 - Low  
**Effort:** 4-6 hours  
**Impact:** Faster queries, better UX

**Solution:**
- Analyze slow queries
- Add composite indexes for common patterns
- Optimize JSONB queries
- Add query result caching

---

### 10. Data Quality Dashboard
**Priority:** P3 - Low  
**Effort:** 8-12 hours  
**Impact:** Better visibility into data quality

**Solution:**
- Create frontend dashboard
- Show quality metrics in real-time
- Visualize quality trends
- Alert on quality issues

---

## Implementation Timeline

**Week 1:**
- ✅ Fix classification pipeline (Issue #1, #2)
- ✅ Run classification on all grants
- ✅ Re-generate procurement signals

**Week 2:**
- ✅ Expand department mapping (Issue #3)
- ✅ Unify scoring systems (Issue #4)
- ✅ Improve quarantine tracking (Issue #5)

**Week 3:**
- ✅ Add missing indexes (Issue #7)
- ✅ Fix future dates validation (Issue #6)
- ✅ Improve pipeline reliability (Issue #8)

**Month 2:**
- Automated monitoring
- Performance optimization
- Quality dashboard

---

## Success Metrics

**Target Metrics (After Fixes):**
- Classification Rate: 90%+ (currently 2.3%)
- Procurement Signal Coverage: 100% (currently 2.3%)
- Department Matching: 95%+ (currently 2.3%)
- Pipeline Success Rate: 90%+ (currently 55%)
- Data Completeness: 100% (maintain current)

**Monitoring:**
- Run `data_quality_monitoring.sql` weekly
- Track metrics over time
- Set up alerts for degradation
