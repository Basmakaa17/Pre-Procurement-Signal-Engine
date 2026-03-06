// In production (browser on Vercel) we call our own /api/proxy, which fetches from Railway at request time.
// Set NEXT_PUBLIC_API_URL or API_URL in Vercel to your Railway backend URL.
function getApiBaseUrl(): string {
  if (typeof window !== "undefined" && !window.location.origin.includes("localhost")) {
    return "/api/proxy"; // server-side proxy reads backend URL from env at request time
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

// TypeScript interfaces matching backend schemas

export interface GrantPreview {
  id: string;
  recipient_name: string;
  amount_cad: number | null;
  award_date: string | null;
}

export interface ProcurementSignal {
  id: string;
  signal_name: string;
  funding_theme: string;
  procurement_category: string;
  department_cluster: string | null;
  region: string | null;
  total_funding_cad: number | null;
  grant_count: number;
  earliest_grant_date: string | null;
  latest_grant_date: string | null;
  time_horizon_min_months: number | null;
  time_horizon_max_months: number | null;
  confidence_score: number | null;
  signal_strength: string | null;
  predicted_rfp_window_start: string | null;
  predicted_rfp_window_end: string | null;
  supporting_grant_ids: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  supporting_grants_preview?: GrantPreview[];
  supporting_grants?: any[];
  rfp_predictions?: {
    signal_name: string;
    aggregated_rfps: {
      rfp_type: string;
      estimated_rfp_count_min: number;
      estimated_rfp_count_max: number;
      timeline_months_min: number;
      timeline_months_max: number;
      likelihood: string;
      target_bidders: string[];
    }[];
    summary: string;
  };
}

export interface RFPPrediction {
  rfp_type: string;
  timeline_months_min: number;
  timeline_months_max: number;
  likelihood: 'high' | 'medium' | 'low';
  target_bidders: string[];
  reasoning: string;
  predicted_rfp_date_start: string | null;
  predicted_rfp_date_end: string | null;
}

export interface GrantRecord {
  id: string;
  source: string;
  source_record_id: string | null;
  issuer_canonical: string;
  issuer_raw: string | null;
  recipient_name: string;
  recipient_name_normalized: string | null;
  recipient_type: string | null;
  agreement_type: string | null;
  amount_cad: number | null;
  amount_unknown: boolean;
  award_date: string | null;
  fiscal_year: string | null;
  region: string | null;
  description: string | null;
  funding_theme: string | null;
  procurement_category: string | null;
  sector_tags: string[] | null;
  llm_confidence: number | null;
  llm_classified_at: string | null;
  quality_flags: any[] | null;
  business_relevance: 'high' | 'medium' | 'low' | 'unknown' | null;
  business_relevance_score: number | null;
  business_relevance_reasons: string[] | null;
  procurement_signal_score: number | null;
  procurement_signal_category: 'high' | 'medium' | 'low' | 'noise' | null;
  procurement_signal_reasons: string[] | null;
  grant_duration_months: number | null;
  predicted_rfps: RFPPrediction[] | null;
  rfp_forecast_summary: string | null;
  rfp_forecast_confidence: string | null;
  predicted_rfp_count: number | null;
  is_quarantined: boolean;
  dedup_hash: string | null;
  raw_data: any | null;
  created_at: string;
  updated_at: string;
}

export interface GrantStats {
  total_grants: number;
  total_funding_cad: number;
  sources: Record<string, number>;
  regions: Record<string, number>;
  themes: Record<string, number>;
  business_relevance?: {
    high: number;
    medium: number;
    low: number;
    unknown: number;
  };
  procurement_signal?: {
    high: number;
    medium: number;
    low: number;
    noise: number;
    unscored: number;
  };
  quarantined_count: number;
  avg_llm_confidence: number;
  last_pipeline_run: string | null;
}

export interface PipelineRun {
  id: string;
  source: string;
  started_at: string;
  completed_at: string | null;
  status: string | null;
  records_fetched: number;
  records_cleaned: number;
  records_quarantined: number;
  records_classified: number;
  records_found?: number | null;
  records_new?: number | null;
  records_existing?: number | null;
  records_with_issues?: number | null;
  records_deduplicated?: number | null;
  records_enriched?: number | null;
  error_message: string | null;
  metadata: Record<string, any>;
}

export interface SearchResult {
  id: string;
  source: string;
  issuer_canonical: string;
  recipient_name: string;
  amount_cad: number | null;
  award_date: string | null;
  region: string | null;
  description: string | null;
  funding_theme: string | null;
  procurement_category: string | null;
  relevance_snippet: string | null;
}

export interface ThemeStats {
  theme: string;
  count: number;
  total_funding: number;
}

export interface OverviewData {
  grants: {
    total: number;
    total_funding_cad: number;
    sources: Record<string, number>;
    regions: Record<string, number>;
    themes: Record<string, number>;
    quarantined_count: number;
    avg_llm_confidence: number;
    business_relevance?: {
      high: number;
      medium: number;
      low: number;
      unknown: number;
    };
    procurement_signal?: {
      high: number;
      medium: number;
      low: number;
      noise: number;
      unscored: number;
    };
  };
  signals: {
    total: number;
    total_funding_cad: number;
    strengths: {
      strong: number;
      moderate: number;
      weak: number;
    };
  };
  last_pipeline_run: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
}

// API Functions

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI<HealthResponse>("/health");
}

export async function fetchOverview(): Promise<OverviewData> {
  return fetchAPI<OverviewData>("/api/overview");
}

export async function fetchSignals(params?: {
  region?: string;
  theme?: string;
  strength?: string;
}): Promise<ProcurementSignal[]> {
  const searchParams = new URLSearchParams();
  if (params?.region) searchParams.append("region", params.region);
  if (params?.theme) searchParams.append("theme", params.theme);
  if (params?.strength) searchParams.append("strength", params.strength);

  const query = searchParams.toString();
  return fetchAPI<ProcurementSignal[]>(
    `/api/signals${query ? `?${query}` : ""}`
  );
}

export async function fetchSignalById(id: string): Promise<ProcurementSignal> {
  return fetchAPI<ProcurementSignal>(`/api/signals/${id}`);
}

export async function fetchGrants(params?: {
  source?: string;
  region?: string;
  theme?: string;
  businessRelevance?: 'high' | 'medium' | 'low' | 'all' | Array<'high' | 'medium' | 'low'>;
  procurementSignal?: 'high' | 'medium' | 'low' | 'noise' | 'all' | Array<'high' | 'medium' | 'low' | 'noise'>;
  quarantined?: boolean;
  limit?: number;
  offset?: number;
}): Promise<{ grants: GrantRecord[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.source) searchParams.append("source", params.source);
  if (params?.region) searchParams.append("region", params.region);
  if (params?.theme) searchParams.append("theme", params.theme);
  
  // Handle business relevance filter (single value or array)
  if (params?.businessRelevance) {
    if (params.businessRelevance !== 'all') {
      if (Array.isArray(params.businessRelevance)) {
        params.businessRelevance.forEach(level => {
          searchParams.append("business_relevance", level);
        });
      } else {
        searchParams.append("business_relevance", params.businessRelevance);
      }
    }
  }
  // Handle procurement signal filter
  if (params?.procurementSignal) {
    if (params.procurementSignal !== 'all') {
      if (Array.isArray(params.procurementSignal)) {
        params.procurementSignal.forEach(level => {
          searchParams.append("procurement_signal", level);
        });
      } else {
        searchParams.append("procurement_signal", params.procurementSignal);
      }
    }
  }
  if (params?.quarantined !== undefined)
    searchParams.append("quarantined", String(params.quarantined));
  if (params?.limit) searchParams.append("limit", String(params.limit));
  if (params?.offset) searchParams.append("offset", String(params.offset));

  const query = searchParams.toString();
  const response = await fetch(`${getApiBaseUrl()}/api/grants${query ? `?${query}` : ""}`);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  const total = parseInt(response.headers.get("X-Total-Count") || "0", 10);
  const grants = await response.json();

  return { grants, total };
}

export async function fetchGrantStats(): Promise<GrantStats> {
  return fetchAPI<GrantStats>("/api/grants/stats");
}

export async function searchGrants(q: string): Promise<SearchResult[]> {
  return fetchAPI<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}`);
}

export async function triggerPipeline(): Promise<{ run_id: string }> {
  const response = await fetchAPI<{ run_id: string; status: string; message: string }>(
    "/api/pipeline/run",
    {
      method: "POST",
      body: JSON.stringify({
        sources: ["open_canada"],
        run_classification: true,
      }),
    }
  );
  return { run_id: response.run_id };
}

export async function fetchPipelineStatus(runId: string): Promise<PipelineRun[]> {
  return fetchAPI<PipelineRun[]>(`/api/pipeline/status/${runId}`);
}

export async function fetchSignalThemes(): Promise<ThemeStats[]> {
  return fetchAPI<ThemeStats[]>("/api/signals/themes");
}
