# Pipeline Flow

## Overview

The pipeline transforms raw government grant data into actionable procurement signals through 6 stages.

```
Data Sources → Adapters → Cleaning → Classification → RFP Prediction → Signal Generation
```

## Stage 1: Fetching (Adapters)

**Location**: `backend/app/adapters/`

| Adapter | Source | Method |
|---------|--------|--------|
| `OpenCanadaAdapter` | Open Canada CKAN API | HTTP + CSV download, supports bulk/incremental |
| `InnovationCanadaAdapter` | Innovation Canada Benefits Finder | Paginated JSON API |
| `ProactiveDisclosureAdapter` | Federal Proactive Disclosure CSVs | CSV download + fuzzy column matching |
| `CSVFileAdapter` | Local CSV file | Pandas CSV reader with flexible column mapping |
| `MockGrantsAdapter` | Generated test data | In-memory generation for demos |

Each adapter outputs `RawGrantRecord` objects with: source, issuer, recipient, amount, date, description, region.

## Stage 2: Cleaning & Normalization

**Location**: `backend/app/pipeline/cleaner.py` + `orchestrator.py`

1. **Text cleaning** — strip HTML, normalize whitespace, remove artifacts
2. **Amount parsing** — handles `$`, commas, "N/A", returns `(float, flags)`
3. **Date parsing** — multiple formats via `dateutil`, extracts fiscal year
4. **Department canonicalization** — fuzzy matches abbreviations to canonical names (e.g., "DND" → "Department of National Defence")
5. **Recipient normalization** — lowercased, stripped, type classification (company/individual/org)
6. **Region extraction** — maps province names to 2-letter codes
7. **Deduplication** — SHA256 hash of `dept + recipient + amount_bucket + fiscal_year`
8. **Quarantining** — records with critical issues flagged but still stored
9. **Business relevance scoring** — classifies grants as high/medium/low relevance to procurement

## Stage 3: Classification (Hybrid)

**Location**: `backend/app/intelligence/rule_classifier.py` + `classifier.py`

The `HybridClassifier` uses a two-tier approach:

1. **Rule-based first** (~80% of grants match):
   - Department → theme mapping (e.g., "Department of National Defence" → "Cybersecurity Modernization")
   - Keyword → theme matching from description text
   - Returns `ClassificationResult` with confidence 0.75-0.85

2. **LLM fallback** (remaining ~20%):
   - Sends grant to configured LLM provider (Groq/OpenAI/Gemini/Anthropic)
   - Returns theme, category, sector tags, confidence, reasoning
   - **Auto-learning**: new keyword patterns from LLM results are added to the rule set

## Stage 4: RFP Prediction

**Location**: `backend/app/intelligence/rfp_predictor.py`

For each classified grant, predicts specific upcoming RFP types:

- **12 funding themes** → each maps to 3-5 specific RFP types
- Each prediction includes: name, value range (% of grant), timeline (months), likelihood, target bidders
- Example: "Cybersecurity Modernization" grant of $500K →
  - Penetration Testing RFP ($25K-$75K, 3-6 months, high likelihood)
  - Security Operations Center RFP ($100K-$250K, 6-12 months, medium likelihood)

## Stage 5: Signal Generation

**Location**: `backend/app/intelligence/signal_detector.py`

Groups classified grants into procurement signals:

1. Groups by `(funding_theme, procurement_category, region)`
2. Applies thresholds: ≥3 grants OR ≥$1M total, within 18 months
3. Calculates confidence (base + volume bonus + recency bonus)
4. Assigns strength: Strong ($10M+), Moderate ($1M+), Weak (minimum)
5. Predicts RFP window: `latest_grant_date + taxonomy_lag_months`
6. Upserts to `procurement_signals` table with supporting grant IDs

## API Trigger

```bash
# Via API
POST /api/pipeline/run
{
  "sources": ["open_canada"],
  "run_classification": true
}

# Via CLI
cd backend && source venv/bin/activate
python -c "
import asyncio
from app.pipeline.orchestrator import PipelineOrchestrator
asyncio.run(PipelineOrchestrator().run(sources=['open_canada']))
"
```

## Error Handling

| Stage | Error Behavior |
|-------|---------------|
| Fetching | Log error, continue with other records/sources |
| Cleaning | Flag quality issues, quarantine if critical |
| Classification | Rule-based fallback → "Unknown" theme at low confidence |
| RFP Prediction | Skip grant if no theme match, log warning |
| Signal Generation | Log error, continue with other groups |
