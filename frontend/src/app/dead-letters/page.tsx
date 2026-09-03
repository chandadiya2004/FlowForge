"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { DeadLetter } from "@/lib/types";

export default function DeadLettersPage() {
  const { user } = useAuth();
  const [deadLetters, setDeadLetters] = useState<DeadLetter[]>([]);
  const [loading, setLoading] = useState(true);
  const [requeueingId, setRequeueingId] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const fetchDeadLetters = async () => {
    try {
      const data = await api.get<DeadLetter[]>("/dead-letters");
      setDeadLetters(data);
    } catch (err: unknown) {
      console.error("Failed to load dead letters:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === "admin") {
      fetchDeadLetters();
    } else {
      setLoading(false);
    }
  }, [user]);

  // Client-side role enforcement
  if (user && user.role !== "admin") {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/40 p-8 text-center">
        <h2 className="text-xl font-bold text-red-300">Access Denied</h2>
        <p className="mt-2 text-sm text-red-200">
          Administrator privileges are required to inspect and requeue dead-letter tasks.
        </p>
        <div className="mt-6">
          <Link
            href="/workflows"
            className="rounded-md bg-gray-800 px-4 py-2 text-sm font-semibold text-gray-200 hover:bg-gray-700"
          >
            Return to Workflows
          </Link>
        </div>
      </div>
    );
  }

  const handleRequeue = async (id: string) => {
    setRequeueingId(id);
    setFeedbackMsg(null);
    try {
      await api.post(`/dead-letters/${id}/requeue`);
      setFeedbackMsg(`Task successfully requeued into pipeline.`);
      await fetchDeadLetters();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to requeue";
      setFeedbackMsg(`Failed to requeue: ${msg}`);
    } finally {
      setRequeueingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Dead-Letter Queue</h1>
          <p className="text-sm text-gray-400">
            Inspect exhausted tasks and trigger manual recovery (Admin Only)
          </p>
        </div>
        <button
          onClick={fetchDeadLetters}
          className="rounded-md bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-200 hover:bg-gray-700"
        >
          ↻ Refresh List
        </button>
      </div>

      {feedbackMsg && (
        <div className="rounded-md border border-indigo-800 bg-indigo-950/60 p-3 text-xs text-indigo-300">
          {feedbackMsg}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading dead letters...</div>
      ) : deadLetters.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-800 p-12 text-center text-gray-400">
          No dead-letter tasks recorded. All pipelines healthy!
        </div>
      ) : (
        <div className="space-y-4">
          {deadLetters.map((dl) => (
            <div
              key={dl.id}
              className="rounded-xl border border-gray-800 bg-gray-900 p-5 shadow space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-gray-800/80 pb-3">
                <div className="flex items-center space-x-3">
                  <span className="rounded bg-red-950 px-2 py-0.5 text-xs font-mono font-bold text-red-400 border border-red-800">
                    {dl.task_type}
                  </span>
                  <span className="text-xs text-gray-400">
                    Failed after <strong className="text-white">{dl.retry_count} retries</strong>
                  </span>
                  {dl.requeued_at && (
                    <span className="rounded bg-emerald-950 px-2 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-800">
                      Requeued: {new Date(dl.requeued_at).toLocaleTimeString()}
                    </span>
                  )}
                </div>

                <div>
                  <button
                    onClick={() => handleRequeue(dl.id)}
                    disabled={requeueingId === dl.id}
                    className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow hover:bg-indigo-500 disabled:opacity-50"
                  >
                    {requeueingId === dl.id ? "Requeueing..." : "Requeue Task"}
                  </button>
                </div>
              </div>

              {/* Context Links */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono text-gray-400">
                <div>
                  <span className="text-gray-500">Task: </span>
                  <span>{dl.task_id}</span>
                </div>
                <div>
                  <span className="text-gray-500">Job: </span>
                  <Link href={`/jobs/${dl.job_id}`} className="text-indigo-400 hover:underline">
                    {dl.job_id.substring(0, 8)}...
                  </Link>
                </div>
                <div>
                  <span className="text-gray-500">Workflow: </span>
                  <Link href={`/workflows/${dl.workflow_id}`} className="text-indigo-400 hover:underline">
                    {dl.workflow_id.substring(0, 8)}...
                  </Link>
                </div>
              </div>

              {/* Error Message */}
              <div className="rounded bg-black/50 p-3 text-xs font-mono text-red-300 border border-red-900/30">
                <span className="font-bold text-red-400">Error: </span>
                {dl.error_message || "No error details recorded"}
              </div>

              <div className="text-right text-xs text-gray-500">
                Recorded at: {new Date(dl.failed_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
