"use client";

import { useState, useEffect } from "react";
import { fetchPipelineStatus } from "@/lib/api";
import { PipelineRun } from "@/lib/api";

interface PipelineStatusModalProps {
  runId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function PipelineStatusModal({
  runId,
  isOpen,
  onClose,
}: PipelineStatusModalProps) {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  // Fetch pipeline status
  const fetchStatus = async () => {
    if (!runId) return;
    
    try {
      setIsLoading(true);
      const data = await fetchPipelineStatus(runId);
      setRuns(data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch pipeline status:", err);
      setError("Failed to fetch pipeline status");
    } finally {
      setIsLoading(false);
    }
  };

  // Setup polling when modal is opened
  useEffect(() => {
    if (isOpen && runId) {
      fetchStatus();
      
      // Poll every 3 seconds
      const interval = setInterval(fetchStatus, 3000);
      setRefreshInterval(interval);
      
      return () => {
        if (refreshInterval) clearInterval(refreshInterval);
      };
    } else {
      if (refreshInterval) clearInterval(refreshInterval);
    }
  }, [isOpen, runId]);

  // Check if any run is still running
  const isAnyRunning = runs.some(run => run.status === "running");
  
  // Calculate overall status
  const getOverallStatus = () => {
    if (runs.some(run => run.status === "failed")) return "failed";
    if (runs.every(run => run.status === "completed")) return "completed";
    return "running";
  };
  
  const overallStatus = getOverallStatus();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white border border-gray-200 rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-heading font-medium text-gray-800">Pipeline Status Details</h2>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        
        {isLoading && runs.length === 0 ? (
          <div className="py-8 text-center">
            <div className="inline-block h-8 w-8 border-4 border-t-[#634086] border-gray-200 rounded-full animate-spin mb-4"></div>
            <p className="text-gray-500">Loading pipeline status...</p>
          </div>
        ) : error ? (
          <div className="py-8 text-center text-[#f59e0b]">
            <svg className="h-12 w-12 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <p>{error}</p>
          </div>
        ) : (
          <>
            {/* Overall status */}
            <div className="flex items-center mb-6 bg-gray-100 p-3 rounded-lg">
              <div className={`h-3 w-3 rounded-full mr-3 ${
                overallStatus === "completed" ? "bg-[#10b981]" : 
                overallStatus === "failed" ? "bg-[#f59e0b]" : 
                "bg-[#634086] animate-pulse"
              }`}></div>
              <div>
                <div className="text-sm text-gray-500">Overall Status</div>
                <div className="font-medium text-gray-800">
                  {overallStatus === "completed" ? "Completed" : 
                   overallStatus === "failed" ? "Failed" : 
                   "Running"}
                </div>
              </div>
              {isAnyRunning && (
                <div className="ml-auto text-xs text-gray-500">
                  Auto-refreshing...
                </div>
              )}
            </div>
            
            {/* Pipeline runs table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-200">
                    <th className="pb-2">Source</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Fetched</th>
                    <th className="pb-2">Cleaned</th>
                    <th className="pb-2">Classified</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id} className="border-b border-gray-200">
                      <td className="py-3 text-gray-700">{run.source}</td>
                      <td className="py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${
                          run.status === "completed" ? "bg-[#10b981]/20 text-[#10b981]" :
                          run.status === "failed" ? "bg-[#f59e0b]/20 text-[#f59e0b]" :
                          "bg-[#634086]/20 text-[#634086]"
                        }`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="py-3">{run.records_fetched}</td>
                      <td className="py-3">{run.records_cleaned}</td>
                      <td className="py-3">{run.records_classified}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Detailed Progress Stats */}
            {runs.some(run => run.records_new !== null || run.records_existing !== null) && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Detailed Progress</h3>
                <div className="space-y-3">
                  {runs.map((run) => (
                    <div key={`${run.id}-details`} className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs font-medium text-gray-600 mb-2">{run.source}</div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {run.records_new !== null && run.records_new !== undefined && (
                          <div>
                            <span className="text-gray-500">New Records:</span>
                            <span className="ml-2 font-medium text-green-600">{run.records_new}</span>
                          </div>
                        )}
                        {run.records_existing !== null && run.records_existing !== undefined && (
                          <div>
                            <span className="text-gray-500">Existing (Deduped):</span>
                            <span className="ml-2 font-medium text-blue-600">{run.records_existing}</span>
                          </div>
                        )}
                        {run.records_enriched !== null && run.records_enriched !== undefined && run.records_enriched > 0 && (
                          <div>
                            <span className="text-gray-500">Enriched:</span>
                            <span className="ml-2 font-medium text-purple-600">{run.records_enriched}</span>
                          </div>
                        )}
                        {run.records_with_issues !== null && run.records_with_issues !== undefined && run.records_with_issues > 0 && (
                          <div>
                            <span className="text-gray-500">With Issues:</span>
                            <span className="ml-2 font-medium text-orange-600">{run.records_with_issues}</span>
                          </div>
                        )}
                        {run.records_quarantined > 0 && (
                          <div>
                            <span className="text-gray-500">Quarantined:</span>
                            <span className="ml-2 font-medium text-red-600">{run.records_quarantined}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Error messages */}
            {runs.some(run => run.error_message) && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-gray-300 mb-2">Error Messages</h3>
                <div className="space-y-2">
                  {runs.filter(run => run.error_message).map((run) => (
                    <div key={`${run.id}-error`} className="bg-[#f59e0b]/10 text-[#f59e0b] p-3 rounded text-xs">
                      <div className="font-medium mb-1">{run.source}</div>
                      <div className="font-mono">{run.error_message}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Processing timeline */}
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Processing Timeline</h3>
              <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-2.5 top-0 h-full w-0.5 bg-gray-200"></div>
                
                {/* Timeline events */}
                <div className="space-y-4 ml-6">
                  {runs.map((run) => (
                    <div key={`${run.id}-timeline`}>
                      <div className="flex items-center">
                        <div className={`absolute left-2 w-3 h-3 rounded-full ${
                          run.status === "completed" ? "bg-[#10b981]" :
                          run.status === "failed" ? "bg-[#f59e0b]" :
                          "bg-[#634086]"
                        }`}></div>
                        <div className="text-xs text-gray-500">
                          {new Date(run.started_at).toLocaleTimeString()}
                        </div>
                      </div>
                      <div className="text-sm mt-1 text-gray-700">Started {run.source} pipeline</div>
                      
                      {run.completed_at && (
                        <>
                          <div className="flex items-center mt-2">
                            <div className={`absolute left-2 w-3 h-3 rounded-full ${
                              run.status === "completed" ? "bg-[#10b981]" :
                              "bg-[#f59e0b]"
                            }`}></div>
                            <div className="text-xs text-gray-500">
                              {new Date(run.completed_at).toLocaleTimeString()}
                            </div>
                          </div>
                          <div className="text-sm mt-1 text-gray-700">
                            {run.status === "completed" ? "Completed" : "Failed"} {run.source} pipeline
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
        
        <div className="mt-6 pt-4 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#634086] hover:bg-[#4F3269] text-white rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}