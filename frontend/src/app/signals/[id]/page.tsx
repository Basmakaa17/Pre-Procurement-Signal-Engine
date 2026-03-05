"use client";

import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { fetchSignalById, ProcurementSignal } from "@/lib/api";
import { SkeletonCard } from "@/components/SkeletonLoader";

function ExpandableDescription({ description }: { description: string }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };
  
  if (!description || description.length < 50) {
    return <div className="mt-1 text-xs text-gray-500">{description}</div>;
  }
  
  return (
    <div className="mt-1">
      <div className="relative">
        <div className={`text-xs text-gray-500 ${isExpanded ? "" : "line-clamp-1"}`}>
          {description}
          {!isExpanded && (
            <span className="inline-block ml-1">...</span>
          )}
        </div>
        <button 
          onClick={handleClick}
          className="text-xs text-[#634086] hover:text-[#50336b] mt-1 inline-block transition-colors"
        >
          {isExpanded ? "Show less" : "Show more"}
        </button>
      </div>
    </div>
  );
}

export default function SignalDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const { data: signal, isLoading } = useSWR<ProcurementSignal>(
    id ? `signal-${id}` : null,
    () => fetchSignalById(id)
  );

  const formatCurrency = (amount: number | null) => {
    if (!amount) return "N/A";
    if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
    if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
    return `$${amount.toLocaleString()}`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white p-8">
        <div className="max-w-6xl mx-auto">
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (!signal) {
    return (
      <div className="min-h-screen bg-white p-8">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-lg p-8 text-center text-gray-500 border border-gray-200 shadow-sm">
            Signal not found
          </div>
        </div>
      </div>
    );
  }

  const confidence = signal.confidence_score ? Math.round(signal.confidence_score * 100) : 0;
  const lagMonths = signal.time_horizon_min_months || 0;

  return (
    <div className="min-h-screen bg-white p-8">
      <div className="max-w-6xl mx-auto">
        <Link
          href="/"
          className="text-sm text-[#634086] hover:text-[#4F3269] transition-colors mb-6 inline-block"
        >
          ← Back to Dashboard
        </Link>

        {/* Signal Header */}
        <div className="bg-white rounded-lg p-6 mb-6 border border-gray-200 shadow-sm">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="font-heading text-3xl font-bold text-gray-800 mb-2">{signal.signal_name}</h1>
              <div className="text-gray-600">
                {signal.funding_theme} → {signal.procurement_category}
              </div>
            </div>
            <div
              className={`px-4 py-2 rounded-full text-sm font-semibold ${
                confidence >= 85
                  ? "bg-[#10b981]/20 text-[#10b981]"
                  : confidence >= 70
                  ? "bg-[#f59e0b]/20 text-[#f59e0b]"
                  : "bg-gray-400/20 text-gray-500"
              }`}
            >
              {confidence}% Confidence
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-4">
            <div>
              <div className="text-xs text-gray-500 mb-1">Total Funding</div>
              <div className="text-lg text-gray-800">{formatCurrency(signal.total_funding_cad)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Grant Count</div>
              <div className="text-lg text-gray-800">{signal.grant_count}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Signal Strength</div>
              <div className="text-lg text-gray-800 capitalize">{signal.signal_strength}</div>
            </div>
          </div>
        </div>

        {/* Forecast Timeline */}
        <div className="bg-white rounded-lg p-6 mb-6 border border-gray-200 shadow-sm">
          <h2 className="font-heading text-xl font-bold text-gray-800 mb-4">Forecast Timeline</h2>
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm text-gray-600">
                {signal.earliest_grant_date && formatDate(signal.earliest_grant_date)}
              </div>
              <div className="text-sm text-gray-600">
                {signal.latest_grant_date && formatDate(signal.latest_grant_date)}
              </div>
              <div className="text-sm text-gray-600">
                {signal.predicted_rfp_window_end && formatDate(signal.predicted_rfp_window_end)}
              </div>
            </div>
            <div className="relative h-12 bg-gray-100 rounded-lg overflow-hidden">
              {/* Grant Period */}
              {signal.earliest_grant_date && signal.latest_grant_date && (
                <div
                  className="absolute left-0 top-0 h-full bg-[#634086] opacity-50"
                  style={{
                    width: "40%",
                  }}
                >
                  <div className="absolute inset-0 flex items-center justify-center text-xs text-white">
                    Grant Period
                  </div>
                </div>
              )}
              {/* Gap */}
              <div className="absolute left-[40%] top-0 h-full w-[10%] bg-gray-200" />
              {/* Predicted Window */}
              {signal.predicted_rfp_window_start && signal.predicted_rfp_window_end && (
                <div
                  className="absolute right-0 top-0 h-full bg-[#634086]"
                  style={{
                    width: "50%",
                  }}
                >
                  <div className="absolute inset-0 flex items-center justify-center text-xs text-white">
                    Predicted RFP Window
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Why This Signal */}
        <div className="bg-white rounded-lg p-6 mb-6 border border-gray-200 shadow-sm">
          <h2 className="font-heading text-xl font-bold text-gray-800 mb-4">Why This Signal?</h2>
          <p className="text-gray-700 leading-relaxed">
            Based on historical analysis, {signal.funding_theme.toLowerCase()} grants have consistently
            led to {signal.procurement_category.toLowerCase()} procurement opportunities within{" "}
            {signal.time_horizon_min_months}-{signal.time_horizon_max_months} months. This signal is
            derived from {signal.grant_count} grants totaling {formatCurrency(signal.total_funding_cad)},
            with a confidence score of {confidence}% based on historical patterns and grant volume.
          </p>
        </div>

        {/* RFP Predictions */}
        {signal.rfp_predictions && signal.rfp_predictions.aggregated_rfps && signal.rfp_predictions.aggregated_rfps.length > 0 && (
          <div className="bg-white rounded-lg p-6 mb-6 border border-[#634086] border-opacity-30 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xl">🎯</span>
              <h2 className="font-heading text-xl font-bold text-gray-800">Predicted RFP Opportunities</h2>
            </div>
            
            {signal.rfp_predictions.summary && (
              <p className="text-sm text-gray-600 mb-4 italic">{signal.rfp_predictions.summary}</p>
            )}
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-[#634086]/5 rounded-lg p-4">
                <div className="text-xs text-gray-500 mb-1">Expected RFP Types</div>
                <div className="text-lg font-semibold text-[#634086]">
                  {signal.rfp_predictions.aggregated_rfps.length} categories
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {signal.rfp_predictions.aggregated_rfps.map((rfp: any, idx: number) => (
                <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-100 hover:border-[#634086]/30 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="text-sm font-semibold text-gray-800">{rfp.rfp_type}</h4>
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                      rfp.likelihood === 'high' 
                        ? 'bg-green-100 text-green-700' 
                        : rfp.likelihood === 'medium'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      {rfp.likelihood} likelihood
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-gray-500">Expected RFPs:</span>
                      <div className="font-mono text-gray-800 font-medium">
                        {rfp.estimated_rfp_count_min}-{rfp.estimated_rfp_count_max}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-500">Timeline:</span>
                      <div className="font-mono text-gray-800 font-medium">
                        {rfp.timeline_months_min}-{rfp.timeline_months_max} months
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {rfp.target_bidders.map((bidder: string, bIdx: number) => (
                      <span key={bIdx} className="text-[10px] px-2 py-0.5 bg-[#634086]/10 text-[#634086] rounded-full">
                        {bidder}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Supporting Grants Table */}
        <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h2 className="font-heading text-xl font-bold text-gray-800 mb-4">
            Supporting Grants ({signal.supporting_grants?.length || 0})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {["Recipient", "Issuer", "Amount", "Date", "Region", "Theme"].map((header) => (
                    <th
                      key={header}
                      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {signal.supporting_grants && signal.supporting_grants.length > 0 ? (
                  signal.supporting_grants.map((grant: any) => (
                    <tr key={grant.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-sm text-gray-800">
                        <div className="flex flex-col">
                          <span>{grant.recipient_name}</span>
                          {grant.description && (
                            <ExpandableDescription description={grant.description} />
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{grant.issuer_canonical}</td>
                      <td className="px-4 py-3 text-sm text-gray-800">
                        {formatCurrency(grant.amount_cad)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {formatDate(grant.award_date)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{grant.region || "N/A"}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {grant.funding_theme || "N/A"}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No supporting grants available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
