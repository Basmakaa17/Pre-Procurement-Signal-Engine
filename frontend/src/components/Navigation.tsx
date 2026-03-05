"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { triggerPipeline, fetchOverview } from "@/lib/api";
import useSWR from "swr";
import PipelineStatusIndicator from "./PipelineStatusIndicator";

export default function Navigation() {
  const pathname = usePathname();
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);

  const isLandingPage = pathname === "/";

  const { data: overview } = useSWR(
    isLandingPage ? null : "overview",
    fetchOverview,
    { refreshInterval: 60000 }
  );

  useEffect(() => {
    if (overview?.last_pipeline_run) {
      const updateTime = new Date(overview.last_pipeline_run);
      const now = new Date();
      const diffMinutes = Math.floor((now.getTime() - updateTime.getTime()) / 60000);
      setLastUpdated(`${diffMinutes} minutes ago`);
    }
  }, [overview]);

  const handleRunPipeline = async () => {
    setIsRunningPipeline(true);
    setCurrentRunId(null);
    try {
      const result = await triggerPipeline();
      setCurrentRunId(result.run_id);
      setIsRunningPipeline(true);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    } catch (error) {
      console.error("Failed to run pipeline:", error);
      setIsRunningPipeline(false);
      setCurrentRunId(null);
    }
  };
  
  const handlePipelineStatusChange = (isStillRunning: boolean) => {
    if (!isStillRunning) {
      setIsRunningPipeline(false);
      setTimeout(() => {
        setCurrentRunId(null);
      }, 15000);
    } else {
      setIsRunningPipeline(true);
    }
  };

  if (isLandingPage) return null;

  return (
    <>
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Left: Logo + Nav Links */}
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center gap-2 no-underline">
                <img 
                  src="https://d41ru60qohkrm.cloudfront.net/PublicusLogo.png" 
                  alt="Publicus Logo" 
                  className="h-8 w-8" 
                />
                <span className="font-heading text-xl font-bold text-[#634086]">PUBLICUS</span>
                <span className="font-mono text-sm text-gray-600">Signal Engine</span>
              </Link>
              <div className="hidden sm:flex items-center gap-1 ml-4">
                <Link
                  href="/dashboard"
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    pathname === "/dashboard"
                      ? "bg-[#634086]/10 text-[#634086]"
                      : "text-gray-500 hover:text-gray-800 hover:bg-gray-100"
                  }`}
                >
                  Dashboard
                </Link>
                <Link
                  href="/grants"
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    pathname === "/grants"
                      ? "bg-[#634086]/10 text-[#634086]"
                      : "text-gray-500 hover:text-gray-800 hover:bg-gray-100"
                  }`}
                >
                  Grants
                </Link>
              </div>
            </div>

            {/* Right: Run Pipeline Button */}
            <button
              onClick={handleRunPipeline}
              disabled={isRunningPipeline}
              className="px-4 py-2 bg-[#634086] hover:bg-[#4F3269] text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isRunningPipeline ? (
                <>
                  <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Running...
                </>
              ) : (
                "Run Pipeline"
              )}
            </button>
          </div>

          {/* Status Bar */}
          <div className="mt-2 text-xs text-gray-600">
            Last updated: {lastUpdated || "Never"}
          </div>
        </div>
      </nav>

      {/* Toast Notification */}
      {showToast && (
        <div className="fixed top-20 right-6 bg-[#10b981] text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-slide-in">
          Pipeline started successfully
        </div>
      )}
      
      {/* Pipeline Status Indicator */}
      <PipelineStatusIndicator 
        runId={currentRunId}
        isRunning={isRunningPipeline}
        onStatusChange={handlePipelineStatusChange}
      />
    </>
  );
}
