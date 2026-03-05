"use client";

import { useState, useMemo } from "react";
import { useDebounce } from "@/hooks/useDebounce";
import useSWR from "swr";
import {
  fetchGrants,
  searchGrants,
  fetchGrantStats,
  GrantRecord,
  SearchResult,
  RFPPrediction,
} from "@/lib/api";
import { SkeletonCard } from "@/components/SkeletonLoader";

function GrantCard({ grant }: { grant: GrantRecord | SearchResult }) {
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [isRFPExpanded, setIsRFPExpanded] = useState(false);
  
  const formatCurrency = (amount: number | null) => {
    if (!amount) return "N/A";
    if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
    return `$${amount.toLocaleString()}`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getConfidenceBadge = (confidence: number | null) => {
    if (!confidence) return { color: "bg-gray-400", text: "N/A" };
    const percent = Math.round(confidence * 100);
    if (percent >= 85) return { color: "bg-[#10b981]", text: `${percent}%` };
    if (percent >= 70) return { color: "bg-[#f59e0b]", text: `${percent}%` };
    return { color: "bg-red-600", text: `${percent}%` };
  };
  
  const getRelevanceBadge = (relevance: string | null, score: number | null) => {
    if (!relevance) return { color: "bg-gray-400", text: "Unknown", textColor: "text-white" };
    const percent = score ? Math.round(score * 100) : null;
    
    if (relevance === 'high') {
      return { 
        color: "bg-green-100", 
        text: `High Business Relevance ${percent ? `(${percent}%)` : ''}`,
        textColor: "text-green-800"
      };
    } else if (relevance === 'medium') {
      return { 
        color: "bg-yellow-100", 
        text: `Medium Business Relevance ${percent ? `(${percent}%)` : ''}`,
        textColor: "text-yellow-800"
      };
    } else {
      return { 
        color: "bg-red-100", 
        text: `Low Business Relevance ${percent ? `(${percent}%)` : ''}`,
        textColor: "text-red-800"
      };
    }
  };

  const getSignalBadge = (category: string | null, score: number | null) => {
    if (!category) return null;
    const s = score ?? 0;
    if (category === 'high') return { color: "bg-emerald-600", text: `RFP Signal: High (${s})`, textColor: "text-white" };
    if (category === 'medium') return { color: "bg-amber-500", text: `RFP Signal: Medium (${s})`, textColor: "text-white" };
    if (category === 'low') return { color: "bg-orange-400", text: `RFP Signal: Low (${s})`, textColor: "text-white" };
    return { color: "bg-gray-400", text: `RFP Signal: Noise (${s})`, textColor: "text-white" };
  };

  const toggleDescription = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDescriptionExpanded(!isDescriptionExpanded);
  };

  const confidence = "llm_confidence" in grant && grant.llm_confidence !== undefined 
    ? grant.llm_confidence 
    : null;
  const confidenceBadge = getConfidenceBadge(confidence);
  const qualityFlags = "quality_flags" in grant ? grant.quality_flags : null;
  
  // Get business relevance badge
  const relevance = "business_relevance" in grant ? grant.business_relevance : null;
  const relevanceScore = "business_relevance_score" in grant ? grant.business_relevance_score : null;
  const relevanceBadge = getRelevanceBadge(relevance, relevanceScore);

  // Get procurement signal badge
  const signalCategory = "procurement_signal_category" in grant ? grant.procurement_signal_category : null;
  const signalScore = "procurement_signal_score" in grant ? grant.procurement_signal_score : null;
  const signalBadge = getSignalBadge(signalCategory, signalScore);

  // Get agreement type & duration
  const agreementType = "agreement_type" in grant ? grant.agreement_type : null;
  const durationMonths = "grant_duration_months" in grant ? grant.grant_duration_months : null;

  return (
    <div className="bg-white rounded-lg p-5 border border-gray-200 shadow-sm hover:border-[#634086] transition-colors">
      {/* Business Relevance Banner - Only show for grants with business_relevance */}
      {"business_relevance" in grant && grant.business_relevance && (
        <div className={`-mx-5 -mt-5 mb-4 px-5 py-2 rounded-t-lg ${relevanceBadge.color}`}>
          <div className="flex items-center justify-between">
            <span className={`text-sm font-medium ${relevanceBadge.textColor}`}>
              {relevanceBadge.text}
            </span>
            {signalBadge && (
              <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${signalBadge.color} ${signalBadge.textColor}`}>
                {signalBadge.text}
              </span>
            )}
          </div>
        </div>
      )}
      
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-800 mb-1">
            {grant.recipient_name || "Unknown Recipient"}
          </h3>
          <div className="text-sm text-gray-600">
            {grant.issuer_canonical || "Unknown Organization"}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {qualityFlags && qualityFlags.length > 0 && (
              <div className="relative group">
              <svg
                className="w-5 h-5 text-[#f59e0b] cursor-help"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <div className="absolute right-0 top-6 w-48 bg-white border border-gray-200 rounded-lg p-2 text-xs text-gray-700 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 shadow-sm">
                Quality flags: {qualityFlags.join(", ")}
              </div>
            </div>
          )}
          <span className={`px-2 py-1 rounded text-xs font-mono ${confidenceBadge.color} text-white`}>
            {confidenceBadge.text}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-gray-500 mb-1">Amount</div>
          <div className="font-mono text-gray-800">
            {formatCurrency(grant.amount_cad)}
          </div>
        </div>
        <div>
          <div className="text-gray-500 mb-1">Date</div>
          <div className="font-mono text-gray-800">
            {formatDate(grant.award_date)}
          </div>
        </div>
      </div>
      
      {grant.description && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-500 mb-1">Description</div>
          <div className="relative">
            <div className={`text-xs text-gray-700 ${isDescriptionExpanded ? "" : "line-clamp-2"}`}>
              {grant.description}
              {!isDescriptionExpanded && grant.description.length > 100 && (
                <span className="inline-block ml-1">...</span>
              )}
            </div>
            <button 
              onClick={toggleDescription}
              className="text-xs text-[#634086] hover:text-[#50336b] transition-colors mt-1 inline-block"
            >
              {isDescriptionExpanded ? "Show less" : "Show more"}
            </button>
          </div>
        </div>
      )}
      
      {/* Metadata row: region, agreement type, duration */}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {grant.region && (
          <div>
            <span className="text-xs text-gray-500">Region: </span>
            <span className="text-xs text-[#634086]">{grant.region}</span>
          </div>
        )}
        {agreementType && (
          <div>
            <span className="text-xs text-gray-500">Type: </span>
            <span className="text-xs text-[#634086] capitalize">{agreementType}</span>
          </div>
        )}
        {durationMonths != null && durationMonths > 0 && (
          <div>
            <span className="text-xs text-gray-500">Duration: </span>
            <span className="text-xs text-[#634086]">{durationMonths} mo</span>
          </div>
        )}
      </div>

      {/* RFP Predictions Section */}
      {"predicted_rfps" in grant && grant.predicted_rfps && grant.predicted_rfps.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsRFPExpanded(!isRFPExpanded);
            }}
            className="flex items-center justify-between w-full text-left"
          >
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-[#634086]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <span className="text-xs font-semibold text-[#634086]">
                🎯 {grant.predicted_rfps.length} Predicted RFP{grant.predicted_rfps.length > 1 ? 's' : ''}
              </span>
            </div>
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform ${isRFPExpanded ? "rotate-180" : ""}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {isRFPExpanded && (
            <div className="mt-2 space-y-2">
              {grant.rfp_forecast_summary && (
                <p className="text-xs text-gray-600 italic mb-2">{grant.rfp_forecast_summary}</p>
              )}
              {grant.predicted_rfps.map((rfp: RFPPrediction, idx: number) => (
                <div key={idx} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                  <div className="flex items-start justify-between mb-1">
                    <span className="text-xs font-semibold text-gray-800">{rfp.rfp_type}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                      rfp.likelihood === 'high' 
                        ? 'bg-green-100 text-green-700' 
                        : rfp.likelihood === 'medium'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      {rfp.likelihood}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-gray-600">
                    <span>{rfp.timeline_months_min}-{rfp.timeline_months_max} months</span>
                    {rfp.predicted_rfp_date_start && (
                      <>
                        <span>•</span>
                        <span>
                          {new Date(rfp.predicted_rfp_date_start).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
                          {" – "}
                          {rfp.predicted_rfp_date_end && new Date(rfp.predicted_rfp_date_end).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
                        </span>
                      </>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {rfp.target_bidders.map((bidder: string, bIdx: number) => (
                      <span key={bIdx} className="text-[10px] px-1.5 py-0.5 bg-[#634086]/10 text-[#634086] rounded">
                        {bidder}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {"funding_theme" in grant && grant.funding_theme && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <span className="text-xs text-gray-500">Theme: </span>
          <span className="text-xs text-[#634086] font-medium">{grant.funding_theme}</span>
          {confidence !== null && (
            <span className="text-xs text-gray-500 ml-2">
              (LLM confidence: {Math.round(confidence * 100)}%)
            </span>
          )}
        </div>
      )}

      {"relevance_snippet" in grant && grant.relevance_snippet && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-500 mb-1">Relevance</div>
          <div className="text-xs text-gray-700 italic">{grant.relevance_snippet}</div>
        </div>
      )}
    </div>
  );
}

export default function GrantsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [regionFilter, setRegionFilter] = useState("");
  const [themeFilter, setThemeFilter] = useState("");
  const [businessRelevanceFilter, setBusinessRelevanceFilter] = useState("all");
  const [confidenceThreshold, setConfidenceThreshold] = useState(0);
  const [page, setPage] = useState(0);
  const [activeTab, setActiveTab] = useState("relevant"); // "relevant" or "non-relevant"
  const pageSize = 20;

  const debouncedSearch = useDebounce(searchQuery, 500);

  const { data: stats } = useSWR("grant-stats", fetchGrantStats);

  const { data: searchResults, isLoading: searchLoading } = useSWR<SearchResult[]>(
    debouncedSearch.length >= 2 ? ["search", debouncedSearch] : null,
    () => searchGrants(debouncedSearch)
  );

  // Determine relevance filter based on active tab
  const relevanceForTab = useMemo((): 'high' | 'medium' | 'low' | ('high' | 'medium' | 'low')[] => {
    if (activeTab === "relevant") {
      if (businessRelevanceFilter === "high" || businessRelevanceFilter === "medium") {
        return businessRelevanceFilter;
      }
      return ["high", "medium"] as ('high' | 'medium' | 'low')[];
    }
    return "low";
  }, [activeTab, businessRelevanceFilter]);

  const { data: grantsData, isLoading: grantsLoading } = useSWR(
    debouncedSearch.length < 2
      ? [
          "grants",
          sourceFilter,
          regionFilter,
          themeFilter,
          relevanceForTab,
          confidenceThreshold,
          page,
          activeTab,
        ]
      : null,
    () =>
      fetchGrants({
        source: sourceFilter || undefined,
        region: regionFilter || undefined,
        theme: themeFilter || undefined,
        businessRelevance: relevanceForTab,
        limit: pageSize,
        offset: page * pageSize,
      })
  );

  const displayGrants = useMemo(() => {
    if (debouncedSearch.length >= 2 && searchResults) {
      // Search results don't have llm_confidence, so we can't filter by confidence
      return searchResults;
    }
    if (grantsData?.grants) {
      return grantsData.grants.filter((grant) => {
        if (confidenceThreshold > 0 && grant.llm_confidence !== null) {
          return grant.llm_confidence >= confidenceThreshold;
        }
        return true;
      });
    }
    return [];
  }, [debouncedSearch, searchResults, grantsData, confidenceThreshold]);

  const totalPages = debouncedSearch.length < 2 && grantsData
    ? Math.ceil(grantsData.total / pageSize)
    : 1;

  return (
    <div className="min-h-screen bg-white p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="font-heading text-3xl font-bold text-gray-800 mb-6">Grant Explorer</h1>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 mb-6">
          <button
            className={`py-3 px-6 font-medium text-sm ${
              activeTab === "relevant"
                ? "text-[#634086] border-b-2 border-[#634086]"
                : "text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => {
              setActiveTab("relevant");
              setPage(0); // Reset pagination when switching tabs
            }}
          >
            Business Relevant Grants
          </button>
          <button
            className={`py-3 px-6 font-medium text-sm ${
              activeTab === "non-relevant"
                ? "text-[#634086] border-b-2 border-[#634086]"
                : "text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => {
              setActiveTab("non-relevant");
              setPage(0); // Reset pagination when switching tabs
            }}
          >
            Non-Relevant Grants
          </button>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search grants by description, recipient, issuer, theme..."
            className="w-full bg-white border border-gray-200 rounded-lg px-4 py-3 text-gray-800 placeholder-gray-500 focus:outline-none focus:border-[#634086] transition-colors shadow-sm"
          />
        </div>

        <div className="grid grid-cols-4 gap-6">
          {/* Filters Sidebar */}
          <div className="col-span-1">
            <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm space-y-4">
              <div>
                <label className="text-xs text-gray-500 mb-2 block">Source</label>
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700"
                >
                  <option value="">All Sources</option>
                  {stats?.sources && Object.keys(stats.sources).map((source) => (
                    <option key={source} value={source}>
                      {source} ({stats.sources[source]})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-gray-500 mb-2 block">Region</label>
                <select
                  value={regionFilter}
                  onChange={(e) => setRegionFilter(e.target.value)}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700"
                >
                  <option value="">All Regions</option>
                  {stats?.regions && Object.keys(stats.regions).map((region) => (
                    <option key={region} value={region}>
                      {region} ({stats.regions[region]})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-gray-500 mb-2 block">Theme</label>
                <select
                  value={themeFilter}
                  onChange={(e) => setThemeFilter(e.target.value)}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700"
                >
                  <option value="">All Themes</option>
                  {stats?.themes && Object.keys(stats.themes).map((theme) => (
                    <option key={theme} value={theme}>
                      {theme} ({stats.themes[theme]})
                    </option>
                  ))}
                </select>
              </div>

              {activeTab === "relevant" && (
                <div>
                  <label className="text-xs text-gray-500 mb-2 block">Business Relevance</label>
                  <select
                    value={businessRelevanceFilter}
                    onChange={(e) => setBusinessRelevanceFilter(e.target.value)}
                    className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700"
                  >
                    <option value="all">All Relevant (High+Medium)</option>
                    <option value="high">High Business Relevance</option>
                    <option value="medium">Medium Business Relevance</option>
                  </select>
                </div>
              )}

              <div>
                <label className="text-xs text-gray-500 mb-2 block">
                  Confidence: {Math.round(confidenceThreshold * 100)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                  className="w-full accent-[#634086]"
                />
              </div>
            </div>
          </div>

          {/* Results Grid */}
          <div className="col-span-3">
            {searchLoading || grantsLoading ? (
              <div className="grid grid-cols-2 gap-4">
                {[...Array(6)].map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            ) : displayGrants.length > 0 ? (
              <>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {displayGrants.map((grant) => (
                    <GrantCard key={grant.id} grant={grant} />
                  ))}
                </div>

                {/* Pagination */}
                {debouncedSearch.length < 2 && totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => setPage(Math.max(0, page - 1))}
                      disabled={page === 0}
                      className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:border-[#634086] transition-colors shadow-sm"
                    >
                      Previous
                    </button>
                    <span className="text-sm text-gray-600">
                      Page {page + 1} of {totalPages}
                    </span>
                    <button
                      onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                      disabled={page >= totalPages - 1}
                      className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:border-[#634086] transition-colors shadow-sm"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="bg-white rounded-lg p-8 text-center text-gray-500 border border-gray-200 shadow-sm">
                No grants found. Try adjusting your filters or run the pipeline to fetch grants.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
