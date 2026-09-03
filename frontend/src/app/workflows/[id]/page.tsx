"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Workflow } from "@/lib/types";

export default function WorkflowDetailPage() {
  const { id } = useParams();
  const router = useRouter();

  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit State
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDefinition, setEditDefinition] = useState("");
  const [editError, setEditError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Trigger Modal State
  const [showTriggerModal, setShowTriggerModal] = useState(false);
  const [priority, setPriority] = useState(5);
  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  const fetchWorkflow = async () => {
    try {
      const data = await api.get<Workflow>(`/workflows/${id}`);
      setWorkflow(data);
      setEditName(data.name);
      setEditDescription(data.description || "");
      setEditDefinition(JSON.stringify(data.definition, null, 2));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load workflow";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchWorkflow();
    }
  }, [id]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setEditError(null);

    let parsedDef: unknown[];
    try {
      parsedDef = JSON.parse(editDefinition) as unknown[];
      if (!Array.isArray(parsedDef) || parsedDef.length === 0) {
        throw new Error("Definition must be a non-empty array.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setEditError(`Invalid JSON: ${msg}`);
      return;
    }

    setSaving(true);
    try {
      const updated = await api.put<Workflow>(`/workflows/${id}`, {
        name: editName,
        description: editDescription || undefined,
        definition: parsedDef,
      });
      setWorkflow(updated);
      setEditing(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update workflow";
      setEditError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to deactivate/delete this workflow?")) return;
    try {
      await api.delete(`/workflows/${id}`);
      router.push("/workflows");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Error deleting workflow: ${msg}`);
    }
  };

  const handleTriggerJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setTriggering(true);
    setTriggerError(null);

    try {
      // 1. Create Job with specified priority
      const newJob = await api.post<{ id: string }>(`/workflows/${id}/jobs`, { priority });
      // 2. Trigger Job
      await api.post(`/jobs/${newJob.id}/trigger`);
      // 3. Navigate to Job detail
      router.push(`/jobs/${newJob.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to trigger job";
      setTriggerError(msg);
      setTriggering(false);
    }
  };

  if (loading) {
    return <div className="py-12 text-center text-gray-500">Loading workflow details...</div>;
  }

  if (error || !workflow) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/40 p-6 text-center text-red-300">
        {error || "Workflow not found"}
        <div className="mt-4">
          <Link href="/workflows" className="text-indigo-400 underline hover:text-indigo-300">
            Back to workflows
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-800 pb-4">
        <div>
          <div className="flex items-center space-x-3">
            <Link href="/workflows" className="text-sm text-gray-400 hover:text-white">
              ← Workflows
            </Link>
            <span className="text-gray-600">/</span>
            <span className="text-xs font-mono text-gray-500">{workflow.id}</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold text-white">{workflow.name}</h1>
          <p className="text-sm text-gray-400">{workflow.description || "No description provided."}</p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowTriggerModal(true)}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-emerald-500 transition flex items-center space-x-2"
          >
            <span>▶ Trigger Job</span>
          </button>
          <button
            onClick={() => setEditing(!editing)}
            className="rounded-md bg-gray-800 px-3 py-2 text-sm font-medium text-gray-200 hover:bg-gray-700"
          >
            {editing ? "Cancel Edit" : "Edit"}
          </button>
          <button
            onClick={handleDelete}
            className="rounded-md bg-red-950/60 border border-red-800 px-3 py-2 text-sm font-medium text-red-300 hover:bg-red-900"
          >
            Delete
          </button>
        </div>
      </div>

      {editing ? (
        <form onSubmit={handleUpdate} className="rounded-xl border border-gray-800 bg-gray-900 p-6 space-y-4">
          <h2 className="text-lg font-bold text-white">Edit Workflow</h2>
          {editError && (
            <div className="rounded border border-red-800 bg-red-950/50 p-3 text-sm text-red-300">
              {editError}
            </div>
          )}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">Name</label>
            <input
              type="text"
              required
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">Description</label>
            <input
              type="text"
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">Task Steps JSON</label>
            <textarea
              rows={10}
              value={editDefinition}
              onChange={(e) => setEditDefinition(e.target.value)}
              className="mt-1 w-full font-mono rounded border border-gray-700 bg-gray-950 p-3 text-xs text-gray-200"
            />
          </div>
          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
            <h2 className="text-lg font-bold text-white mb-4">Pipeline Steps ({workflow.definition.length})</h2>
            <div className="space-y-3">
              {workflow.definition.map((step, idx) => (
                <div
                  key={idx}
                  className="flex flex-col sm:flex-row sm:items-center justify-between rounded-lg border border-gray-800 bg-gray-950 p-4"
                >
                  <div className="flex items-center space-x-4">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-950 border border-indigo-700 text-xs font-bold text-indigo-300">
                      {idx + 1}
                    </span>
                    <div>
                      <h4 className="font-semibold text-white">{step.name}</h4>
                      <span className="inline-block rounded bg-gray-800 px-2 py-0.5 text-xs font-mono text-gray-300">
                        {step.type}
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 sm:mt-0 font-mono text-xs text-gray-400 max-w-md truncate">
                    {JSON.stringify(step.config)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Trigger Job Modal */}
      {showTriggerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Trigger Workflow Execution</h3>
            <p className="mt-1 text-sm text-gray-400">Configure run parameters for {workflow.name}</p>

            {triggerError && (
              <div className="mt-3 rounded border border-red-800 bg-red-950/50 p-2 text-xs text-red-300">
                {triggerError}
              </div>
            )}

            <form onSubmit={handleTriggerJob} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Priority Level (1 to 10)
                </label>
                <div className="mt-2 flex items-center space-x-4">
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={priority}
                    onChange={(e) => setPriority(parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                  <span className="font-mono text-lg font-bold text-indigo-400 w-6 text-center">
                    {priority}
                  </span>
                </div>
                <div className="mt-1 flex justify-between text-xs text-gray-500">
                  <span>1 (High Queue)</span>
                  <span>5 (Default Queue)</span>
                  <span>10 (Low Queue)</span>
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowTriggerModal(false)}
                  className="px-3 py-1.5 text-sm text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={triggering}
                  className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {triggering ? "Dispatching..." : "Run Job Now"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
