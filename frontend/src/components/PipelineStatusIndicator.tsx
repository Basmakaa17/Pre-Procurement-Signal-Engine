"use client";

import { useState, useEffect } from "react";
import { fetchPipelineStatus } from "@/lib/api";
import { PipelineRun } from "@/lib/api";
import PipelineStatusModal from "./PipelineStatusModal";

interface PipelineStatusIndicatorProps {
  runId?: string | null;
  isRunning: boolean;
  onStatusChange?: (isStillRunning: boolean) => void;
}

export default function PipelineStatusIndicator({
  runId,
  isRunning,
  onStatusChange,
}: PipelineStatusIndicatorProps) {
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "failed">(
    isRunning ? "running" : "idle"
  );
  const [progress, setProgress] = useState<number>(0);
  const [stats, setStats] = useState<{
    fetched: number;
    cleaned: number;
    classified: number;
    total: number;
  }>({
    fetched: 0,
    cleaned: 0,
    classified: 0,
    total: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Poll for status updates when a pipeline is running
  useEffect(() => {
    // Show indicator if running OR if we have a runId (even if isRunning is false initially)
    if (!runId) {
      if (!isRunning) {
        setStatus("idle");
      }
      return;
    }

    // Always show if we have a runId
    setStatus("running");
    let isMounted = true;
    let checkInterval: NodeJS.Timeout | null = null;
    
    const checkStatus = async () => {
      try {
        const runs = await fetchPipelineStatus(runId);
        
        if (!isMounted) return;
        
        // If no runs found, keep polling (might be starting)
        if (!runs || runs.length === 0) {
          return;
        }
        
        // Aggregate stats from all sources
        let totalFetched = 0;
        let totalCleaned = 0;
        let totalClassified = 0;
        let isStillRunning = false;
        let hasError = false;
        let errorMsg = "";
        
        runs.forEach(run => {
          totalFetched += run.records_fetched || 0;
          totalCleaned += run.records_cleaned || 0;
          totalClassified += run.records_classified || 0;
          
          if (run.status === "running") {
            isStillRunning = true;
          }
          
          if (run.status === "failed" && run.error_message) {
            hasError = true;
            errorMsg = run.error_message;
          }
        });
        
        // Calculate progress based on pipeline stages
        // Stage 1: Fetching (0-30%)
        // Stage 2: Cleaning (30-60%)
        // Stage 3: Classification (60-90%)
        // Stage 4: Signal Generation (90-100%)
        let calculatedProgress = 0;
        
        if (totalFetched > 0) {
          calculatedProgress = Math.min(30, (totalFetched / Math.max(totalFetched, 1)) * 30);
        }
        if (totalCleaned > 0) {
          calculatedProgress = Math.min(60, 30 + (totalCleaned / Math.max(totalCleaned, 1)) * 30);
        }
        if (totalClassified > 0) {
          calculatedProgress = Math.min(90, 60 + (totalClassified / Math.max(totalClassified, 1)) * 30);
        }
        if (!isStillRunning && totalClassified > 0) {
          calculatedProgress = 100;
        }
        
        // If we have stats but no progress, show at least 5%
        if (calculatedProgress === 0 && (totalFetched > 0 || totalCleaned > 0 || totalClassified > 0)) {
          calculatedProgress = 5;
        }
        
        setStats({
          fetched: totalFetched,
          cleaned: totalCleaned,
          classified: totalClassified,
          total: Math.max(totalFetched, totalCleaned, totalClassified),
        });
        
        setProgress(isStillRunning ? calculatedProgress : 100);
        
        if (hasError) {
          setStatus("failed");
          setError(errorMsg);
          if (onStatusChange) onStatusChange(false);
          if (checkInterval) clearInterval(checkInterval);
        } else if (!isStillRunning && totalClassified > 0) {
          setStatus("completed");
          if (onStatusChange) onStatusChange(false);
          // Keep showing for 10 seconds after completion
          setTimeout(() => {
            if (isMounted) {
              setStatus("idle");
            }
          }, 10000);
          if (checkInterval) clearInterval(checkInterval);
        } else {
          // Still running, keep polling
          setStatus("running");
        }
      } catch (err) {
        console.error("Failed to check pipeline status:", err);
        // Don't stop polling on error, might be temporary
      }
    };
    
    // Check immediately
    checkStatus();
    
    // Then poll every 2 seconds
    checkInterval = setInterval(checkStatus, 2000);
    
    return () => {
      isMounted = false;
      if (checkInterval) clearInterval(checkInterval);
    };
  }, [runId, isRunning, onStatusChange]);

  // Show indicator if we have a runId OR if status is not idle
  if (status === "idle" && !runId) {
    return null;
  }

  return (
    <>
      <div 
        className="fixed bottom-4 right-4 bg-white border border-gray-200 rounded-lg shadow-lg p-4 w-80 z-50 cursor-pointer hover:border-[#634086] transition-colors animate-slide-in-bottom"
        onClick={() => setIsModalOpen(true)}
      >
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-heading font-medium text-gray-800">Pipeline Status</h3>
          {status === "running" ? (
            <span className="flex items-center text-[#634086] text-sm">
              <span className="h-2 w-2 bg-[#634086] rounded-full animate-pulse mr-2"></span>
              Running
            </span>
          ) : status === "completed" ? (
            <span className="flex items-center text-[#10b981] text-sm">
              <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Completed
            </span>
          ) : (
            <span className="flex items-center text-[#f59e0b] text-sm">
              <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              Failed
            </span>
          )}
        </div>
      
      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-3 overflow-hidden">
        <div 
          className={`h-2 rounded-full ${status === "failed" ? "bg-[#f59e0b]" : "bg-[#634086]"}`} 
          style={{ 
            width: `${progress}%`, 
            transition: "width 0.5s ease-in-out",
            boxShadow: status === "running" ? "0 0 10px rgba(99, 64, 134, 0.5)" : "none"
          }}
        >
          {status === "running" && progress < 100 && (
            <div className="h-full w-full bg-[#634086]/30 animate-pulse-custom"></div>
          )}
        </div>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 text-xs text-gray-700 mb-2">
        <div>
          <div className="text-gray-500">Fetched</div>
          <div>{stats.fetched}</div>
        </div>
        <div>
          <div className="text-gray-500">Cleaned</div>
          <div>{stats.cleaned}</div>
        </div>
        <div>
          <div className="text-gray-500">Classified</div>
          <div>{stats.classified}</div>
        </div>
      </div>
      
      {error && (
        <div className="mt-2 text-xs text-[#f59e0b] bg-[#f59e0b]/10 p-2 rounded">
          {error}
        </div>
      )}
      
      {status === "completed" && (
        <div className="mt-2 text-xs text-[#10b981] bg-[#10b981]/10 p-2 rounded">
          Pipeline completed successfully!
        </div>
      )}
        
      <div className="mt-2 text-xs text-center text-gray-500 hover:text-[#634086]">
        Click for details
      </div>
      </div>
      
      {/* Detailed Pipeline Status Modal */}
      <PipelineStatusModal
        runId={runId || null}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  );
}