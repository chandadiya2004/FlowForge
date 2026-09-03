"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Job } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-amber-950/60 text-amber-400 border-amber-800",
  running: "bg-blue-950/60 text-blue-400 border-blue-800 animate-pulse",
  retrying: "bg-orange-950/60 text-orange-400 border-orange-800 animate-pulse",
  completed: "bg-emerald-950/60 text-emerald-400 border-emerald-800",
  failed: "bg-red-950/60 text-red-400 border-red-800",
  cancelled: "bg-gray-800 text-gray-400 border-gray-700",
};

export default function JobDetailPage() {
  const { id } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  // Poll reference
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchJob = async (silent: boolean = false) => {
    try {
      const data = await api.get<Job>(`/jobs/${id}`);
      setJob(data);

      // Terminal status check: stop polling if completed, failed, or cancelled
      const terminalStatuses = ["completed", "failed", "cancelled"];
      if (terminalStatuses.includes(data.status)) {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        setIsPolling(false);
      } else {
        setIsPolling(true);
      }
    } catch (err: unknown) {
      if (!silent) {
        const msg = err instanceof Error ? err.message : "Failed to load job details";
        setError(msg);
      }
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    if (!id) return;

    // Initial fetch
    fetchJob();

    // Start 2s polling
    pollIntervalRef.current = setInterval(() => {
      fetchJob(true);
    }, 2000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [id]);

  if (loading) {
    return <div className="py-12 text-center text-gray-500">Loading job details...</div>;
  }

  if (error || !job) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/40 p-6 text-center text-red-300">
        {error || "Job not found"}
        <div className="mt-4">
          <Link href="/jobs" className="text-indigo-400 underline hover:text-indigo-300">
            Back to jobs
          </Link>
        </div>
      </div>
    );
  }

  const tasks = job.tasks || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-800 pb-4">
        <div>
          <div className="flex items-center space-x-3">
            <Link href="/jobs" className="text-sm text-gray-400 hover:text-white">
              ← Jobs
            </Link>
            <span className="text-gray-600">/</span>
            <span className="text-xs font-mono text-gray-500">{job.id}</span>
          </div>
          <div className="mt-2 flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white">Job Details</h1>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold border ${
                STATUS_COLORS[job.status] || "bg-gray-800 text-gray-300"
              }`}
            >
              {job.status}
            </span>
            {isPolling && (
              <span className="flex items-center space-x-1.5 text-xs text-blue-400">
                <span className="h-2 w-2 rounded-full bg-blue-500 animate-ping"></span>
                <span>Live Polling (2s)</span>
              </span>
            )}
          </div>
        </div>

        <div className="text-sm text-gray-400">
          <Link
            href={`/workflows/${job.workflow_id}`}
            className="rounded-md border border-gray-700 bg-gray-900 px-3 py-1.5 hover:border-indigo-500 hover:text-white"
          >
            View Parent Workflow →
          </Link>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <span className="text-xs font-medium uppercase tracking-wider text-gray-500">Priority Tier</span>
          <p className="mt-1 text-lg font-bold text-white">
            Level {job.priority}{" "}
            <span className="text-xs font-normal text-gray-400">
              ({job.priority <= 3 ? "High" : job.priority <= 7 ? "Default" : "Low"})
            </span>
          </p>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <span className="text-xs font-medium uppercase tracking-wider text-gray-500">Tasks Total</span>
          <p className="mt-1 text-lg font-bold text-white">{tasks.length}</p>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <span className="text-xs font-medium uppercase tracking-wider text-gray-500">Started At</span>
          <p className="mt-1 text-xs text-gray-300">
            {job.started_at ? new Date(job.started_at).toLocaleTimeString() : "Not started"}
          </p>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <span className="text-xs font-medium uppercase tracking-wider text-gray-500">Completed At</span>
          <p className="mt-1 text-xs text-gray-300">
            {job.completed_at ? new Date(job.completed_at).toLocaleTimeString() : "In progress"}
          </p>
        </div>
      </div>

      {/* Task Execution Sequence */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white">Execution Pipeline</h2>
        <div className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900 shadow">
          <table className="min-w-full divide-y divide-gray-800">
            <thead className="bg-gray-950">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Step
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Task Name & Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Retries
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Timing
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-sm">
              {tasks.map((task) => (
                <React.Fragment key={task.id}>
                  <tr className="hover:bg-gray-850/50 transition">
                    <td className="whitespace-nowrap px-6 py-4 font-mono text-xs font-bold text-indigo-400">
                      #{task.sequence}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <div className="font-semibold text-white">{task.name}</div>
                      <div className="font-mono text-xs text-gray-400">{task.type}</div>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium border ${
                          STATUS_COLORS[task.status] || "bg-gray-800 text-gray-300"
                        }`}
                      >
                        {task.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-xs text-gray-300">
                      {task.retry_count} / {task.max_retries}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-xs text-gray-400">
                      {task.started_at ? new Date(task.started_at).toLocaleTimeString() : "—"}
                      {task.completed_at ? ` → ${new Date(task.completed_at).toLocaleTimeString()}` : ""}
                    </td>
                  </tr>

                  {/* Failure Error Message Row */}
                  {task.error_message && (
                    <tr className="bg-red-950/20">
                      <td colSpan={5} className="px-6 py-3 text-xs text-red-300 font-mono border-t border-red-900/40">
                        <span className="font-bold text-red-400">Error: </span>
                        {task.error_message}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
