"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Job } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-amber-950/60 text-amber-400 border-amber-800",
  running: "bg-blue-950/60 text-blue-400 border-blue-800 animate-pulse",
  completed: "bg-emerald-950/60 text-emerald-400 border-emerald-800",
  failed: "bg-red-950/60 text-red-400 border-red-800",
  cancelled: "bg-gray-800 text-gray-400 border-gray-700",
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  const fetchJobs = async () => {
    try {
      const endpoint = statusFilter === "all" ? "/jobs" : `/jobs?status=${statusFilter}`;
      const data = await api.get<Job[]>(endpoint);
      setJobs(data);
    } catch (err: unknown) {
      console.error("Failed to load jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Job Executions</h1>
          <p className="text-sm text-gray-400">Track and inspect distributed workflow runs</p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Filter Status:
          </label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-900 px-3 py-1.5 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading jobs...</div>
      ) : jobs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-800 p-12 text-center text-gray-400">
          No jobs found matching the current filter.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900 shadow">
          <table className="min-w-full divide-y divide-gray-800">
            <thead className="bg-gray-950">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Job ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Workflow
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Priority
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Created At
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-sm">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-850 transition">
                  <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-gray-300">
                    <Link href={`/jobs/${job.id}`} className="text-indigo-400 hover:underline">
                      {job.id.substring(0, 8)}...
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-gray-400">
                    <Link href={`/workflows/${job.workflow_id}`} className="hover:text-gray-200">
                      {job.workflow_id.substring(0, 8)}...
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium border ${
                        STATUS_COLORS[job.status] || "bg-gray-800 text-gray-300"
                      }`}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <span
                      className={`font-semibold text-xs ${
                        job.priority <= 3
                          ? "text-red-400"
                          : job.priority <= 7
                          ? "text-amber-400"
                          : "text-gray-400"
                      }`}
                    >
                      Tier {job.priority} ({job.priority <= 3 ? "high" : job.priority <= 7 ? "default" : "low"})
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-xs text-gray-400">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right">
                    <Link
                      href={`/jobs/${job.id}`}
                      className="rounded bg-gray-800 px-3 py-1 text-xs font-medium text-gray-200 hover:bg-gray-700"
                    >
                      Inspect →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
