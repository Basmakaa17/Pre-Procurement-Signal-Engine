"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  fetchOverview,
  fetchSignals,
  fetchSignalThemes,
  fetchGrants,
  OverviewData,
  ProcurementSignal,
  ThemeStats,
  GrantRecord,
} from "@/lib/api";
import SignalCard from "@/components/SignalCard";
import { SkeletonCard, SkeletonTable } from "@/components/SkeletonLoader";

export default function Dashboard() {
  const [signalFilter, setSignalFilter] = useState<string>("all");
  const [regionFilter, setRegionFilter] = useState<string>("");

  const { data: overview, isLoading: overviewLoading } = useSWR<OverviewData>(
    "overview",
    fetchOverview,
    { refreshInterval: 30000 }
  );

  const { data: signals, isLoading: signalsLoading } = useSWR<ProcurementSignal[]>(
    ["signals", signalFilter, regionFilter],
    () => fetchSignals({
      strength: signalFilter !== "all" ? signalFilter : undefined,
      region: regionFilter || undefined,
    }),
    { refreshInterval: 60000 }
  );

  const { data: themes, isLoading: themesLoading } = useSWR<ThemeStats[]>(
    "themes",
    fetchSignalThemes,
    { refreshInterval: 300000 }
  );

  const { data: grantsData, isLoading: grantsLoading } = useSWR(
    "recent-grants",
    () => fetchGrants({ limit: 20, offset: 0 }),
    { refreshInterval: 60000 }
  );

  const formatCurrency = (amount: number) => {
    if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
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

  const getRelevanceBadge = (relevance: string | null, score: number | null) => {
    if (!relevance) return { color: "bg-gray-400", text: "Unknown", textColor: "text-white" };
    const percent = score ? Math.round(score * 100) : null;
    
    if (relevance === 'high') {
      return { 
        color: "bg-green-600", 
        text: `High ${percent ? `(${percent}%)` : ''}`,
        textColor: "text-white"
      };
    } else if (relevance === 'medium') {
      return { 
        color: "bg-yellow-500", 
        text: `Med ${percent ? `(${percent}%)` : ''}`,
        textColor: "text-white"
      };
    } else {
      return { 
        color: "bg-red-600", 
        text: `Low ${percent ? `(${percent}%)` : ''}`,
        textColor: "text-white"
      };
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Bar */}
        <section className="grid grid-cols-4 gap-4 mb-8">
          {overviewLoading ? (
            [...Array(4)].map((_, i) => (
              <div key={i} className="bg-[#10141c] rounded-md p-4 animate-pulse">
                <div className="h-4 bg-gray-800 rounded w-1/2 mb-2" />
                <div className="h-6 bg-gray-800 rounded w-3/4" />
              </div>
            ))
          ) : overview ? (
            <>
              <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm hover:border-[#634086] transition-colors group cursor-pointer">
                <div className="text-xs text-gray-500 mb-1">Total Grants Processed</div>
                <div className="font-mono text-2xl font-semibold text-gray-800">
                  {overview.grants.total.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  {Object.entries(overview.grants.sources).map(([source, count]) => (
                    <div key={source}>{source}: {count}</div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-xs text-gray-500 mb-1">Total Funding Tracked</div>
                <div className="font-mono text-2xl font-semibold text-gray-800">
                  {formatCurrency(overview.grants.total_funding_cad)}
                </div>
              </div>

              <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-xs text-gray-500 mb-1">Active Signals</div>
                <div className="font-mono text-2xl font-semibold text-gray-800">
                  {overview.signals.total}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {overview.signals.strengths.strong} strong, {overview.signals.strengths.moderate} moderate, {overview.signals.strengths.weak} weak
                </div>
              </div>

              <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                <div className="text-xs text-gray-500 mb-1">RFP Signal (Procurement)</div>
                <div className="font-mono text-2xl font-semibold text-gray-800">
                  {(overview.grants.procurement_signal?.high || 0) + (overview.grants.procurement_signal?.medium || 0)} Actionable
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {overview.grants.procurement_signal?.high || 0} high, {overview.grants.procurement_signal?.medium || 0} medium, {overview.grants.procurement_signal?.low || 0} low, {overview.grants.procurement_signal?.noise || 0} noise
                </div>
              </div>
            </>
          ) : null}
        </section>

        <div className="grid grid-cols-10 gap-6">
          {/* Signal Feed - Left 65% */}
          <section className="col-span-7">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-2 w-2 bg-[#634086] rounded-full animate-pulse" />
                </div>
                <div>
                  <h2 className="font-heading text-2xl font-bold text-gray-800">Procurement Signals</h2>
                  <p className="text-sm text-gray-500">Grant clusters predicting future government procurement</p>
                </div>
              </div>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4 mb-6">
              <div className="flex gap-2">
                {["all", "strong", "moderate", "weak"].map((strength) => (
                  <button
                    key={strength}
                    onClick={() => setSignalFilter(strength)}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      signalFilter === strength
                        ? "bg-[#634086] text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {strength.charAt(0).toUpperCase() + strength.slice(1)}
                  </button>
                ))}
              </div>

              <select
                value={regionFilter}
                onChange={(e) => setRegionFilter(e.target.value)}
                className="bg-white border border-gray-200 rounded-lg px-3 py-1 text-sm text-gray-700"
              >
                <option value="">All Regions</option>
                {overview?.grants.regions && Object.keys(overview.grants.regions).map((region) => (
                  <option key={region} value={region}>{region}</option>
                ))}
              </select>
            </div>

            {/* Signal Cards */}
            <div className="space-y-4">
              {signalsLoading ? (
                [...Array(3)].map((_, i) => <SkeletonCard key={i} />)
              ) : signals && signals.length > 0 ? (
                signals.map((signal) => <SignalCard key={signal.id} signal={signal} />)
              ) : (
                <div className="bg-white rounded-lg p-8 text-center text-gray-500 border border-gray-200 shadow-sm">
                  No signals found. Run the pipeline to generate signals.
                </div>
              )}
            </div>
          </section>

          {/* Sector Momentum - Right 35% */}
          <section className="col-span-3">
            <h2 className="font-heading text-xl font-bold text-gray-800 mb-4">Sector Momentum</h2>
            <div className="bg-white rounded-lg p-4 space-y-4 border border-gray-200 shadow-sm">
              {themesLoading ? (
                <SkeletonTable />
              ) : themes && themes.length > 0 ? (
                themes
                  .sort((a, b) => b.total_funding - a.total_funding)
                  .slice(0, 8)
                  .map((theme, index) => (
                    <div key={theme.theme} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">{theme.theme}</span>
                        <span className="text-xs text-[#634086] font-mono">
                          {formatCurrency(theme.total_funding)}
                        </span>
                      </div>
                      <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#634086]"
                          style={{
                            width: `${(theme.total_funding / (themes[0]?.total_funding || 1)) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))
              ) : (
                <div className="text-sm text-gray-500">No theme data available</div>
              )}
            </div>
          </section>
        </div>

        {/* Recent Grants Table */}
        <section className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading text-xl font-bold text-gray-800">Recent Grants</h2>
            <Link
              href="/grants"
              className="text-sm text-[#634086] hover:text-[#4F3269] transition-colors"
            >
              View All →
            </Link>
          </div>

          <div className="bg-white rounded-lg overflow-hidden border border-gray-200 shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {["Source", "Recipient", "Issuer", "Amount", "Date", "Theme", "RFP Signal", "Relevance"].map(
                      (header) => (
                        <th
                          key={header}
                          className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider"
                        >
                          {header}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {grantsLoading ? (
                    [...Array(5)].map((_, i) => (
                      <tr key={i} className="animate-pulse">
                        {[...Array(8)].map((_, j) => (
                          <td key={j} className="px-4 py-3">
                            <div className="h-4 bg-gray-100 rounded w-20" />
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : grantsData?.grants && grantsData.grants.length > 0 ? (
                    grantsData.grants.map((grant) => {
                      const badge = getRelevanceBadge(grant.business_relevance, grant.business_relevance_score);
                      const signalCat = grant.procurement_signal_category;
                      const signalScore = grant.procurement_signal_score;
                      const signalColor = signalCat === 'high'
                        ? 'bg-emerald-600 text-white'
                        : signalCat === 'medium'
                        ? 'bg-amber-500 text-white'
                        : signalCat === 'low'
                        ? 'bg-orange-400 text-white'
                        : signalCat === 'noise'
                        ? 'bg-gray-400 text-white'
                        : 'bg-gray-200 text-gray-500';
                      return (
                        <tr key={grant.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3 text-sm text-gray-600">{grant.source}</td>
                          <td className="px-4 py-3 text-sm text-gray-800">
                            {grant.recipient_name || "Unknown"}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {grant.issuer_canonical || "Unknown"}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-800">
                            {formatCurrency(grant.amount_cad || 0)}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {formatDate(grant.award_date)}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-700">
                            {grant.funding_theme || (
                              <span className="text-gray-400 italic">Not classified</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${signalColor}`}>
                              {signalCat ? `${signalCat} (${signalScore ?? '?'})` : '—'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${badge.color} ${badge.textColor}`}
                            >
                              {badge.text}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                        No grants found. Run the pipeline to fetch grants.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
