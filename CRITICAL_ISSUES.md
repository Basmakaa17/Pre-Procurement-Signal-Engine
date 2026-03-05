# Critical Issues List
**Priority:** Immediate Action Required

## 🔴 CRITICAL - Fix Immediately

### Issue #1: 97.7% of Grants Unclassified
**Severity:** CRITICAL  
**Impact:** Procurement signals based on only 2.3% of data, system largely ineffective  
**Affected:** 5,073 grants from `open_canada` source

**Symptoms:**
- `funding_theme IS NULL` for 5,073 grants
- `procurement_signal_category IS NULL` for 5,073 grants
- `records_classified: 0` in all recent pipeline runs
- Only 119 CSV grants are fully processed

**Root Cause:**
- Classification pipeline not running for existing grants
- `_classify_grants()` may not be called when `records_new: 0`
- Progress tracking shows `records_cleaned: 0` when all grants already exist

**Fix Required:**
1. Ensure `_classify_grants()` processes ALL unclassified grants from database
2. Modify progress tracking to count existing grants as "cleaned"
3. Run classification script on all 5,073 unclassified grants

**Files to Modify:**
- `backend/app/pipeline/orchestrator.py` - `_classify_grants()` method
- `backend/app/pipeline/orchestrator.py` - Progress tracking logic

**Estimated Effort:** 2-4 hours

---

### Issue #2: Classification Pipeline Not Running
**Severity:** CRITICAL  
**Impact:** No grants being classified, no procurement signals generated  
**Affected:** All 5,073 open_canada grants

**Symptoms:**
- Recent pipeline runs show `records_classified: 0`
- `_classify_grants()` is called but returns 0
- Grants have `dedup_hash` (cleaned) but no `funding_theme` (not classified)

**Root Cause:**
- `_classify_grants()` queries for `funding_theme IS NULL` grants
- Method should work, but may be failing silently
- Need to verify classification is actually running

**Fix Required:**
1. Add logging to `_classify_grants()` to track execution
2. Verify grants are being fetched from database
3. Check if classification is being skipped due to conditions
4. Create script to manually trigger classification

**Files to Modify:**
- `backend/app/pipeline/orchestrator.py` - `_classify_grants()` method
- Add classification monitoring/logging

**Estimated Effort:** 1-2 hours

---

## 🟡 HIGH PRIORITY - Fix This Week

### Issue #3: Department Matching Failure (36.9%)
**Severity:** HIGH  
**Impact:** Poor issuer normalization, affects signal clustering  
**Affected:** 1,915 grants (36.9% of open_canada)

**Symptoms:**
- 1,915 grants flagged with "unknown_department"
- Only 119 grants have successful department matches
- 43 unique issuers in database, but mapping only covers ~20

**Root Cause:**
- `DEPT_CANONICAL` mapping in `cleaner.py` is too limited
- Open Canada has more departments than mapping covers
- Fuzzy matching may not be working for all departments

**Fix Required:**
1. Analyze all 43 unique issuers from open_canada
2. Expand `DEPT_CANONICAL` mapping
3. Improve fuzzy matching algorithm
4. Add fallback matching strategies

**Files to Modify:**
- `backend/app/pipeline/cleaner.py` - `DEPT_CANONICAL` mapping
- `backend/app/pipeline/cleaner.py` - `canonicalize_department()` function

**Estimated Effort:** 4-6 hours

---

### Issue #4: Scoring System Mismatch
**Severity:** HIGH  
**Impact:** Confusion about which scoring system to trust  
**Affected:** 105 grants with conflicting scores

**Symptoms:**
- 21 grants: "high" business relevance but "noise" procurement signal
- 31 grants: "medium" business relevance but "noise" procurement signal
- Average score difference: 30-80 points

**Root Cause:**
- Two different scoring systems (business_relevance vs procurement_signal)
- Systems use different criteria and thresholds
- No clear documentation on when to use each

**Fix Required:**
1. Decide on single scoring system OR clearly document usage
2. Align scoring criteria between systems
3. Update UI to show consistent scoring
4. Add documentation explaining scoring systems

**Files to Modify:**
- `backend/app/intelligence/procurement_signal_score.py`
- `backend/app/intelligence/business_relevance_filter.py`
- Frontend components showing scores

**Estimated Effort:** 2-3 hours

---

### Issue #5: Quarantine Tracking Missing
**Severity:** HIGH  
**Impact:** Cannot trace why records were quarantined  
**Affected:** 524 quarantined records

**Symptoms:**
- All 524 quarantine records have `pipeline_run_id: NULL`
- Cannot determine when/why records were quarantined
- Quarantine reason is "unknown" for all records

**Root Cause:**
- Quarantine records not linked to pipeline runs
- Missing `pipeline_run_id` when creating quarantine records
- Quarantine reason not properly captured

**Fix Required:**
1. Link quarantine records to pipeline runs
2. Capture detailed failure reasons
3. Add pipeline_run_id to quarantine creation
4. Create dashboard for quarantine review

**Files to Modify:**
- `backend/app/pipeline/orchestrator.py` - Quarantine creation
- `backend/app/pipeline/cleaner.py` - Quarantine logic

**Estimated Effort:** 2-3 hours

---

## 🟢 MEDIUM PRIORITY - Fix This Month

### Issue #6: Future Dates (14 grants)
**Severity:** MEDIUM  
**Impact:** Data quality concerns  
**Affected:** 14 grants with dates in 2027

**Fix Required:**
- Investigate source data
- Add validation to reject future dates > 1 year
- Flag for manual review

**Estimated Effort:** 1 hour

---

### Issue #7: Missing Index on procurement_signal_score
**Severity:** MEDIUM  
**Impact:** Performance degradation on filtering/sorting  
**Affected:** All queries filtering by score

**Fix Required:**
- Add index: `CREATE INDEX idx_grant_records_procurement_signal_score ON grant_records(procurement_signal_score DESC)`

**Estimated Effort:** 5 minutes

---

### Issue #8: Pipeline Success Rate (55%)
**Severity:** MEDIUM  
**Impact:** Unreliable pipeline execution  
**Affected:** 14 failed runs, 8 stuck runs

**Fix Required:**
- Investigate failure reasons
- Fix stuck runs
- Improve error handling
- Add retry logic

**Estimated Effort:** 4-6 hours

---

## Implementation Priority

1. **Week 1:** Fix Issues #1 and #2 (Classification)
2. **Week 2:** Fix Issues #3, #4, #5 (Department matching, scoring, quarantine)
3. **Week 3:** Fix Issues #6, #7, #8 (Data quality, performance, reliability)
