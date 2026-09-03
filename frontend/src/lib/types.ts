export type UserRole = "admin" | "member" | "viewer";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface TaskDefinition {
  name: string;
  type: string;
  config: Record<string, unknown>;
  max_retries?: number;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string | null;
  owner_id: string;
  definition: TaskDefinition[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  job_id: string;
  name: string;
  type: string;
  sequence: number;
  status: "pending" | "running" | "completed" | "failed" | "retrying";
  input_data?: Record<string, unknown> | null;
  output_data?: Record<string, unknown> | null;
  error_message?: string | null;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface Job {
  id: string;
  workflow_id: string;
  triggered_by: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  priority: number;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  tasks?: Task[];
}

export interface DeadLetter {
  id: string;
  task_id: string;
  job_id: string;
  workflow_id: string;
  task_type: string;
  input_data?: Record<string, unknown> | null;
  error_message?: string | null;
  retry_count: number;
  failed_at: string;
  requeued_at?: string | null;
}
