import { Page } from "@playwright/test";

/**
 * Shared mock API data and route handlers for E2E tests.
 * All tests use these mocks so they run consistently without a live backend.
 */

export const MOCK_GRANTS = [
  {
    id: "grant-1",
    source: "open_canada",
    source_record_id: "oc-001",
    issuer_canonical: "Department of National Defence",
    issuer_raw: "Department of National Defence",
    recipient_name: "CyberSafe Solutions Inc.",
    recipient_name_normalized: "cybersafe solutions inc",
    recipient_type: "private_company",
    agreement_type: "contribution",
    amount_cad: 2500000,
    amount_unknown: false,
    award_date: "2025-06-15",
    fiscal_year: "2025-2026",
    region: "Ontario",
    description: "Cybersecurity modernization and threat assessment program for federal IT infrastructure.",
    funding_theme: "Cybersecurity Modernization",
    procurement_category: "IT Security",
    sector_tags: ["cybersecurity", "IT"],
    llm_confidence: 0.92,
    llm_classified_at: "2025-06-20T12:00:00Z",
    quality_flags: [],
    business_relevance: "high" as const,
    business_relevance_score: 0.88,
    business_relevance_reasons: ["government_department", "high_amount", "cybersecurity"],
    procurement_signal_score: 78,
    procurement_signal_category: "high" as const,
    procurement_signal_reasons: ["agreement_type:contribution:30", "recipient_type:private_company:25", "keywords_pos:modernization:18", "amount:>=1000000:20"],
    grant_duration_months: 24,
    predicted_rfps: [
      {
        rfp_type: "Penetration Testing & Vulnerability Assessment",
        timeline_months_min: 3,
        timeline_months_max: 6,
        likelihood: "high" as const,
        target_bidders: ["Cybersecurity firms", "IT consulting firms"],
        reasoning: "Based on cybersecurity grant pattern",
        predicted_rfp_date_start: "2025-09-15",
        predicted_rfp_date_end: "2025-12-15",
      },
    ],
    rfp_forecast_summary: "1 predicted RFP opportunity over the next 3-6 months",
    rfp_forecast_confidence: "high",
    predicted_rfp_count: 1,
    is_quarantined: false,
    dedup_hash: "abc123",
    raw_data: null,
    created_at: "2025-06-20T12:00:00Z",
    updated_at: "2025-06-20T12:00:00Z",
  },
  {
    id: "grant-2",
    source: "open_canada",
    source_record_id: "oc-002",
    issuer_canonical: "Health Canada",
    issuer_raw: "Health Canada",
    recipient_name: "MedTech Innovations Ltd.",
    recipient_name_normalized: "medtech innovations ltd",
    recipient_type: "private_company",
    agreement_type: "contribution",
    amount_cad: 1800000,
    amount_unknown: false,
    award_date: "2025-05-10",
    fiscal_year: "2025-2026",
    region: "Quebec",
    description: "Digital health platform development for remote patient monitoring.",
    funding_theme: "Healthcare Digitization",
    procurement_category: "Health IT",
    sector_tags: ["healthcare", "digital"],
    llm_confidence: 0.87,
    llm_classified_at: "2025-06-20T12:00:00Z",
    quality_flags: [],
    business_relevance: "medium" as const,
    business_relevance_score: 0.65,
    business_relevance_reasons: ["healthcare", "digital_platform"],
    procurement_signal_score: 55,
    procurement_signal_category: "medium" as const,
    procurement_signal_reasons: ["agreement_type:contribution:30", "keywords_pos:platform:18,digital:18"],
    grant_duration_months: 18,
    predicted_rfps: null,
    rfp_forecast_summary: null,
    rfp_forecast_confidence: null,
    total_predicted_rfp_value_min: null,
    total_predicted_rfp_value_max: null,
    predicted_rfp_count: null,
    is_quarantined: false,
    dedup_hash: "def456",
    raw_data: null,
    created_at: "2025-06-20T12:00:00Z",
    updated_at: "2025-06-20T12:00:00Z",
  },
];

export const MOCK_LOW_RELEVANCE_GRANT = {
  id: "grant-3",
  source: "open_canada",
  source_record_id: "oc-003",
  issuer_canonical: "SSHRC",
  issuer_raw: "Social Sciences and Humanities Research Council",
  recipient_name: "University of Toronto Student",
  recipient_name_normalized: "university of toronto student",
  recipient_type: "individual",
  agreement_type: "grant",
  amount_cad: 25000,
  amount_unknown: false,
  award_date: "2025-04-01",
  fiscal_year: "2025-2026",
  region: "Ontario",
  description: "Graduate scholarship for social sciences research.",
  funding_theme: "Unknown",
  procurement_category: "Unknown",
  sector_tags: [],
  llm_confidence: 0.55,
  llm_classified_at: "2025-06-20T12:00:00Z",
  quality_flags: ["low_confidence"],
  business_relevance: "low" as const,
  business_relevance_score: 0.15,
  business_relevance_reasons: ["scholarship", "individual_recipient"],
  procurement_signal_score: 0,
  procurement_signal_category: "noise" as const,
  procurement_signal_reasons: ["hard_filter:keyword:scholarship"],
  grant_duration_months: null,
  predicted_rfps: null,
  rfp_forecast_summary: null,
  rfp_forecast_confidence: null,
  total_predicted_rfp_value_min: null,
  total_predicted_rfp_value_max: null,
  predicted_rfp_count: null,
  is_quarantined: false,
  dedup_hash: "ghi789",
  raw_data: null,
  created_at: "2025-06-20T12:00:00Z",
  updated_at: "2025-06-20T12:00:00Z",
};

export const MOCK_SIGNALS = [
  {
    id: "signal-1",
    signal_name: "Ontario Cybersecurity Wave",
    funding_theme: "Cybersecurity Modernization",
    procurement_category: "IT Security",
    department_cluster: "Department of National Defence",
    region: "Ontario",
    total_funding_cad: 18400000,
    grant_count: 14,
    earliest_grant_date: "2025-01-15",
    latest_grant_date: "2025-06-15",
    time_horizon_min_months: 6,
    time_horizon_max_months: 9,
    confidence_score: 0.88,
    signal_strength: "strong",
    predicted_rfp_window_start: "2025-07-15",
    predicted_rfp_window_end: "2026-03-15",
    supporting_grant_ids: ["grant-1"],
    is_active: true,
    created_at: "2025-06-20T12:00:00Z",
    updated_at: "2025-06-20T12:00:00Z",
    supporting_grants_preview: [
      {
        id: "grant-1",
        recipient_name: "CyberSafe Solutions Inc.",
        amount_cad: 2500000,
        award_date: "2025-06-15",
      },
    ],
  },
  {
    id: "signal-2",
    signal_name: "Federal AI Modernization",
    funding_theme: "AI & Machine Learning",
    procurement_category: "Software Development",
    department_cluster: "Treasury Board Secretariat",
    region: "National",
    total_funding_cad: 31200000,
    grant_count: 9,
    earliest_grant_date: "2025-02-01",
    latest_grant_date: "2025-05-20",
    time_horizon_min_months: 3,
    time_horizon_max_months: 6,
    confidence_score: 0.75,
    signal_strength: "moderate",
    predicted_rfp_window_start: "2025-05-01",
    predicted_rfp_window_end: "2025-11-20",
    supporting_grant_ids: [],
    is_active: true,
    created_at: "2025-06-20T12:00:00Z",
    updated_at: "2025-06-20T12:00:00Z",
    supporting_grants_preview: [],
  },
];

export const MOCK_SIGNAL_DETAIL = {
  ...MOCK_SIGNALS[0],
  supporting_grants: [MOCK_GRANTS[0]],
  rfp_predictions: {
    signal_name: "Ontario Cybersecurity Wave",
    aggregated_rfps: [
      {
        rfp_type: "Penetration Testing & Vulnerability Assessment",
        estimated_rfp_count_min: 2,
        estimated_rfp_count_max: 5,
        timeline_months_min: 3,
        timeline_months_max: 6,
        likelihood: "high",
        target_bidders: ["Cybersecurity firms", "IT consulting firms"],
      },
      {
        rfp_type: "Managed Security Operations Center (SOC)",
        estimated_rfp_count_min: 1,
        estimated_rfp_count_max: 3,
        timeline_months_min: 6,
        timeline_months_max: 12,
        likelihood: "medium",
        target_bidders: ["Managed security providers", "IT infrastructure firms"],
      },
    ],
    summary: "Based on $18.4M in cybersecurity grants, we predict 3-8 RFPs over the next 3-12 months.",
  },
};

export const MOCK_OVERVIEW = {
  grants: {
    total: 150,
    total_funding_cad: 85000000,
    sources: { open_canada: 120, innovation_canada: 30 },
    regions: { Ontario: 60, Quebec: 40, "British Columbia": 25, Alberta: 25 },
    themes: {
      "Cybersecurity Modernization": 30,
      "Healthcare Digitization": 25,
      "AI & Machine Learning": 20,
    },
    quarantined_count: 5,
    avg_llm_confidence: 0.82,
    business_relevance: { high: 45, medium: 60, low: 40, unknown: 5 },
    procurement_signal: { high: 12, medium: 33, low: 45, noise: 55, unscored: 5 },
  },
  signals: {
    total: 8,
    total_funding_cad: 65000000,
    strengths: { strong: 3, moderate: 3, weak: 2 },
  },
  last_pipeline_run: new Date(Date.now() - 300000).toISOString(), // 5 min ago
};

export const MOCK_THEMES = [
  { theme: "Cybersecurity Modernization", count: 30, total_funding: 25000000 },
  { theme: "Healthcare Digitization", count: 25, total_funding: 20000000 },
  { theme: "AI & Machine Learning", count: 20, total_funding: 15000000 },
  { theme: "Infrastructure Modernization", count: 15, total_funding: 10000000 },
];

export const MOCK_GRANT_STATS = {
  total_grants: 150,
  total_funding_cad: 85000000,
  sources: { open_canada: 120, innovation_canada: 30 },
  regions: { Ontario: 60, Quebec: 40, "British Columbia": 25, Alberta: 25 },
  themes: {
    "Cybersecurity Modernization": 30,
    "Healthcare Digitization": 25,
    "AI & Machine Learning": 20,
  },
  business_relevance: { high: 45, medium: 60, low: 40, unknown: 5 },
  procurement_signal: { high: 12, medium: 33, low: 45, noise: 55, unscored: 5 },
  quarantined_count: 5,
  avg_llm_confidence: 0.82,
  last_pipeline_run: new Date(Date.now() - 300000).toISOString(),
};

export const MOCK_SEARCH_RESULTS = [
  {
    id: "grant-1",
    source: "open_canada",
    issuer_canonical: "Department of National Defence",
    recipient_name: "CyberSafe Solutions Inc.",
    amount_cad: 2500000,
    award_date: "2025-06-15",
    region: "Ontario",
    description: "Cybersecurity modernization and threat assessment program.",
    funding_theme: "Cybersecurity Modernization",
    procurement_category: "IT Security",
    relevance_snippet: "Matched on: cybersecurity, threat assessment",
  },
];

/**
 * Sets up all API route mocks for a page.
 * Call this in beforeEach to ensure consistent test data.
 */
export async function setupAPIMocks(page: Page) {
  // Overview
  await page.route("**/api/overview", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_OVERVIEW),
    });
  });

  // Signals list (matches with or without query params)
  await page.route(/\/api\/signals(\?.*)?$/, (route) => {
    const url = route.request().url();
    // Don't intercept /api/signals/themes or /api/signals/<id>
    if (url.includes("/api/signals/")) return route.fallback();
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_SIGNALS),
    });
  });

  // Signals themes
  await page.route("**/api/signals/themes", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_THEMES),
    });
  });

  // Signal detail - match /api/signals/<uuid>
  await page.route(/\/api\/signals\/signal-\d+/, (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_SIGNAL_DETAIL),
    });
  });

  // Grants list (with business_relevance filter support)
  await page.route("**/api/grants?**", (route) => {
    const url = route.request().url();
    const params = new URL(url).searchParams;
    const relevanceFilters = params.getAll("business_relevance");

    let grants = [...MOCK_GRANTS, MOCK_LOW_RELEVANCE_GRANT];

    if (relevanceFilters.length > 0) {
      grants = grants.filter((g) => relevanceFilters.includes(g.business_relevance));
    }

    route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: {
        "X-Total-Count": String(grants.length),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(grants),
    });
  });

  // Grant stats
  await page.route("**/api/grants/stats", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_GRANT_STATS),
    });
  });

  // Search
  await page.route("**/api/search?**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_SEARCH_RESULTS),
    });
  });

  // Pipeline run trigger
  await page.route("**/api/pipeline/run", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "test-run-123",
        status: "running",
        message: "Pipeline started",
      }),
    });
  });

  // Pipeline status
  await page.route("**/api/pipeline/status/**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "test-run-123",
          source: "open_canada",
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          status: "completed",
          records_fetched: 50,
          records_cleaned: 48,
          records_quarantined: 2,
          records_classified: 48,
          error_message: null,
          metadata: {},
        },
      ]),
    });
  });

  // Health check
  await page.route("**/health", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "healthy", service: "pre-procurement-signal-engine" }),
    });
  });
}
