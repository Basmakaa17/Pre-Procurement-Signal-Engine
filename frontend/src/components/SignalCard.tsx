"use client";

import { useState } from "react";
import Link from "next/link";
import { ProcurementSignal } from "@/lib/api";

interface SignalCardProps {
  signal: ProcurementSignal;
}

export default function SignalCard({ signal }: SignalCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getStrengthColor = () => {
    switch (signal.signal_strength) {
      case "strong":
        return "border-[#10b981]";
      case "moderate":
        return "border-[#f59e0b]";
      default:
        return "border-gray-400";
    }
  };

  const formatCurrency = (amount: number | null) => {
    if (!amount) return "N/A";
    if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
    if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
    return `$${amount.toLocaleString()}`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  };

  const calculateProgress = () => {
    if (!signal.predicted_rfp_window_start || !signal.predicted_rfp_window_end) return 0;
    const start = new Date(signal.predicted_rfp_window_start).getTime();
    const end = new Date(signal.predicted_rfp_window_end).getTime();
    const now = Date.now();
    if (now < start) return 0;
    if (now > end) return 100;
    return ((now - start) / (end - start)) * 100;
  };

  const confidence = signal.confidence_score ? Math.round(signal.confidence_score * 100) : 0;

  return (
    <div
      className={`bg-white border-l-4 ${getStrengthColor()} rounded-r-lg p-5 hover:shadow-lg hover:border-opacity-100 transition-all cursor-pointer group border-t border-r border-b border-gray-200`}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      {/* Top Row */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="font-heading text-lg font-semibold text-gray-800 mb-1">
            {signal.signal_name}
          </h3>
          <div className="text-sm text-gray-500">
            Department: {signal.department_cluster || "N/A"} • Region: {signal.region || "N/A"}
          </div>
        </div>
        <div
          className={`px-3 py-1 rounded-full text-xs font-mono font-semibold ${
            confidence >= 85
              ? "bg-[#10b981]/20 text-[#10b981]"
              : confidence >= 70
              ? "bg-[#f59e0b]/20 text-[#f59e0b]"
              : "bg-gray-600/20 text-gray-400"
          }`}
        >
          {confidence}%
        </div>
      </div>

      {/* Body */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-xs text-gray-500 mb-1">Total Funding</div>
          <div className="font-mono text-sm text-gray-700">
            {formatCurrency(signal.total_funding_cad)} across {signal.grant_count} grants
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1">Predicted Window</div>
          <div className="font-mono text-sm text-gray-700">
            {formatDate(signal.predicted_rfp_window_start)} – {formatDate(signal.predicted_rfp_window_end)}
          </div>
        </div>
      </div>

      {/* Procurement Category */}
      <div className="flex items-center gap-2 mb-4">
        <svg className="w-4 h-4 text-[#634086]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm text-gray-600">
          Likely Procurement: <span className="font-semibold text-gray-800">{signal.procurement_category}</span>
        </span>
      </div>

      {/* Supporting Evidence */}
      <div className="border-t border-gray-200 pt-4">
        <button
          className="text-xs text-gray-500 hover:text-[#634086] transition-colors mb-2"
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
        >
          {isExpanded ? "▼" : "▶"} Supporting Evidence
        </button>

        {isExpanded && signal.supporting_grants_preview && (
          <div className="flex flex-wrap gap-2 mt-2">
            {signal.supporting_grants_preview.map((grant) => (
              <div
                key={grant.id}
                className="px-2 py-1 bg-gray-100 rounded text-xs font-mono text-gray-700"
              >
                {grant.recipient_name} • {formatCurrency(grant.amount_cad)} • {formatDate(grant.award_date)}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* View Full Signal Link */}
      <div className="mt-4 pt-4 border-t border-gray-200 flex justify-end">
        <Link
          href={`/signals/${signal.id}`}
          className="text-sm text-[#634086] hover:text-[#4F3269] transition-colors font-medium"
          onClick={(e) => e.stopPropagation()}
        >
          View Full Signal →
        </Link>
      </div>
    </div>
  );
}
