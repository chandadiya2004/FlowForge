"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Workflow } from "@/lib/types";

const DEFAULT_SAMPLE_DEFINITION = JSON.stringify(
  [
    {
      name: "Step 1 - Initialize",
      type: "log_message",
      config: { message: "Starting pipeline execution" },
    },
    {
      name: "Step 2 - Sleep Brief Delay",
      type: "sleep",
      config: { seconds: 1 },
    },
    {
      name: "Step 3 - Finalize",
      type: "log_message",
      config: { message: "Pipeline completed successfully" },
    },
  ],
  null,
  2
);

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [definitionJson, setDefinitionJson] = useState(DEFAULT_SAMPLE_DEFINITION);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchWorkflows = async () => {
    try {
      const data = await api.get<Workflow[]>("/workflows");
      setWorkflows(data);
    } catch (err: unknown) {
      console.error("Failed to load workflows:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const handleCreateWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    let parsedDef: unknown[];
    try {
      parsedDef = JSON.parse(definitionJson) as unknown[];
      if (!Array.isArray(parsedDef) || parsedDef.length === 0) {
        throw new Error("Definition must be a non-empty JSON array of task steps.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setFormError(`Invalid JSON definition: ${msg}`);
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/workflows", {
        name,
        description: description || undefined,
        definition: parsedDef,
      });

      // Reset form & reload
      setName("");
      setDescription("");
      setDefinitionJson(DEFAULT_SAMPLE_DEFINITION);
      setShowModal(false);
      await fetchWorkflows();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create workflow";
      setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Workflows</h1>
          <p className="text-sm text-gray-400">Manage and trigger your automated pipelines</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-indigo-500 transition"
        >
          + New Workflow
        </button>
      </div>

      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading workflows...</div>
      ) : workflows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-800 p-12 text-center">
          <p className="text-base font-medium text-gray-300">No workflows found</p>
          <p className="mt-1 text-sm text-gray-500">Create your first workflow to begin executing distributed tasks.</p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            Create Workflow
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workflows.map((wf) => (
            <Link
              key={wf.id}
              href={`/workflows/${wf.id}`}
              className="group block rounded-xl border border-gray-800 bg-gray-900 p-5 shadow transition hover:border-indigo-500 hover:bg-gray-850"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-white group-hover:text-indigo-400 transition truncate">
                  {wf.name}
                </h3>
                <span className="rounded-full bg-emerald-950 px-2 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-800">
                  Active
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-400 line-clamp-2">
                {wf.description || "No description provided."}
              </p>
              <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
                <span>{wf.definition?.length || 0} task steps</span>
                <span>{new Date(wf.created_at).toLocaleDateString()}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* New Workflow Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <h2 className="text-lg font-bold text-white">Create New Workflow</h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-white text-xl"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="mt-4 rounded border border-red-800 bg-red-950/60 p-3 text-sm text-red-300">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateWorkflow} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Workflow Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Daily Data Sync"
                  className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Description
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional brief description"
                  className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">
                    Task Steps (JSON Array) *
                  </label>
                  <span className="text-xs text-gray-500">Supported types: log_message, sleep, http_call</span>
                </div>
                <textarea
                  rows={8}
                  required
                  value={definitionJson}
                  onChange={(e) => setDefinitionJson(e.target.value)}
                  className="mt-1 w-full font-mono rounded border border-gray-700 bg-gray-950 p-3 text-xs text-gray-200 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded px-4 py-2 text-sm font-medium text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  {submitting ? "Saving..." : "Create Workflow"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
