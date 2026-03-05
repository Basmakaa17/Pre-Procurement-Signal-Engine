# Publicus Signal Engine

A procurement intelligence platform that analyzes Canadian government grant data to predict future RFP opportunities. By tracking grant patterns across federal programs, the system identifies funding clusters that historically precede government procurement, enabling businesses to anticipate and prepare for upcoming RFPs.

## What It Does

1. **Ingests** grant data from Open Canada (CKAN API, CSV exports) and other government sources
2. **Cleans & normalizes** messy government data — handling inconsistent formats, missing fields, duplicates, and encoding issues
3. **Classifies** grants into 12 standardized funding themes using a hybrid rule-based + LLM approach
4. **Scores business relevance** — filters out scholarships, academic grants, and non-procurement-related items
5. **Predicts RFP opportunities** — forecasts specific procurement types, estimated values, timelines, and target bidders for each grant
6. **Generates procurement signals** — clusters related grants to identify emerging procurement patterns with confidence scoring

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  Open Canada (CKAN API) · Innovation Canada · CSV Imports       │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  ADAPTERS  (backend/app/adapters/)                               │
│  OpenCanadaAdapter · InnovationCanadaAdapter · CSVFileAdapter    │
│  ProactiveDisclosureAdapter · MockGrantsAdapter                  │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  PIPELINE  (backend/app/pipeline/)                               │
│  Cleaner: amount/date parsing, dept canonicalization,            │
│           recipient normalization, deduplication, quarantining    │
│  Profiler: data quality metrics before/after cleaning            │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  INTELLIGENCE  (backend/app/intelligence/)                       │
│  HybridClassifier: rule-based → LLM fallback, auto-learning     │
│  RelevanceFilter: business relevance scoring (high/medium/low)   │
│  RFP Predictor: per-grant RFP type, value, timeline predictions  │
│  SignalDetector: clusters grants → procurement signals           │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  API  (backend/app/api/)  FastAPI + rate limiting                │
│  /api/grants · /api/signals · /api/pipeline · /api/search        │
│  /api/overview                                                   │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  FRONTEND  (frontend/src/)  Next.js 14 + TypeScript + Tailwind   │
│  Dashboard · Grant Explorer · Signal Detail · Pipeline Controls  │
└──────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Hybrid classification** (rules first, LLM fallback) | 80%+ of grants match keyword/department rules → avoids slow & expensive LLM calls. New LLM results auto-learn back into rule set. |
| **Business relevance scoring** | Government grants include scholarships, academic funding, and other non-procurement items. Scoring surfaces only procurement-relevant grants to users. |
| **RFP prediction engine** | Rule-based mapping from 12 funding themes → specific RFP types with value ranges, timelines, likelihoods, and target bidder types. |
| **Content-based deduplication** | Hash of normalized dept + recipient + amount bucket + fiscal year prevents duplicates across incremental fetches. |
| **Supabase (PostgreSQL)** | Managed database with built-in auth, instant API, and easy SQL migrations. |

## Project Structure

```
Pre-Procurement-Signal-Engine/
├── backend/
│   ├── app/
│   │   ├── adapters/           # Data source adapters (Open Canada, CSV, etc.)
│   │   ├── api/                # FastAPI routes (grants, signals, pipeline, search)
│   │   ├── database/           # Supabase client
│   │   ├── intelligence/       # Classifier, relevance filter, RFP predictor, signal detector
│   │   ├── models/             # Pydantic models (RawGrantRecord, CleanedGrantRecord)
│   │   └── pipeline/           # Cleaner, profiler, orchestrator, source metadata
│   ├── database/
│   │   ├── complete_schema.sql # Full database schema (run for new installs)
│   │   ├── seed_taxonomies.sql # Procurement taxonomy seed data
│   │   └── migrations/         # Incremental schema changes
│   ├── main.py                 # FastAPI app entry point
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js pages (dashboard, grants, signals)
│   │   ├── components/         # Shared React components
│   │   ├── hooks/              # Custom React hooks
│   │   └── lib/                # API client
│   └── package.json
├── PUBLICUS_CONTEXT.txt        # Project brief / business context
├── setup.sh                    # One-command local setup
└── README.md
```

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account and project
- LLM API key (Groq, OpenAI, Gemini, or Anthropic)

### Quick Start

```bash
./setup.sh
```

### Manual Setup

**Backend:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Edit with your credentials
```

**Database:**

1. Open your Supabase SQL Editor
2. Run `backend/database/complete_schema.sql`
3. Run `backend/database/seed_taxonomies.sql`
4. Run any pending files in `backend/database/migrations/`

**Frontend:**

```bash
cd frontend
npm install
cp .env.local.example .env.local    # Edit if needed
```

### Environment Variables

**Backend (.env):**

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `LLM_PROVIDER` | `groq`, `openai`, `gemini`, or `anthropic` |
| `GROQ_API_KEY` / `OPENAI_API_KEY` / etc. | LLM provider API key |
| `ALLOWED_ORIGINS` | CORS origins (use `*` for dev) |

**Frontend (.env.local):**

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://localhost:8000`) |

## Running

```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## How Signals Work

1. **Grant Classification**: Grants are classified into 12 funding themes (e.g., "Cybersecurity Modernization", "Digital Transformation") using rule-based matching with LLM fallback.

2. **Pattern Recognition**: Grants are grouped by theme, category, and region. A signal is generated when a cluster hits thresholds (≥3 grants OR ≥$1M total, within 18 months, ≥70% classification confidence).

3. **RFP Prediction**: Each funding theme maps to specific RFP types. For example, a $500K cybersecurity grant predicts upcoming Penetration Testing RFPs ($25K-$75K, 3-6 months) and Security Operations Center RFPs ($100K-$250K, 6-12 months).

4. **Signal Strength**: Strong ($10M+ or 10+ grants), Moderate ($1M+ or 5+ grants), or Weak (meets minimum).

## Deployment

**Backend → Railway:** Connect GitHub repo, add env vars, deploy. Uses `Procfile` and `railway.json`.

**Frontend → Vercel:** Import repo, set `NEXT_PUBLIC_API_URL` to Railway URL, deploy.

## License

Research prototype. See LICENSE for details.
