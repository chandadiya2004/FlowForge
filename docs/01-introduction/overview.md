# Overview

FlowForge is a resilient, distributed workflow orchestration and background job-processing platform. It allows users and systems to define multi-step workflow pipelines, trigger them on demand as isolated jobs, and rely on the platform to execute each step sequentially with automatic retries, exponential backoff, priority queueing, and poison-task isolation.

---

## The Problem It Solves

Running ad-hoc scripts, cron jobs, or in-process background threads quickly creates operational bottlenecks as systems scale:

1. **Lack of Operational Visibility**: When a scheduled cron job or detached background script fails, diagnosing what went wrong requires hunting through unstructured host logs. FlowForge provides granular, step-by-step execution history with timestamps, input payloads, outputs, and explicit error messages.
2. **Fragile and Missing Retry Logic**: Transient network blips, database locks, or external third-party API rate limits often kill naive scripts midway. FlowForge incorporates configurable per-step retries with exponential backoff so temporary outages resolve without manual intervention.
3. **No Priority Management Under Load**: When hundreds of routine background jobs queue up, critical real-time workflows (such as user-facing notifications or transactional webhooks) get blocked behind slow batch tasks. FlowForge implements priority routing that prioritizes urgent work ahead of standard or bulk processing.
4. **Silent Poison Tasks**: In plain queue setups, a consistently failing task either loops infinitely, crashes workers, or gets discarded silently. FlowForge routes permanently exhausted tasks into a dedicated Dead-Letter table, preserving the full execution state and error stack for operator inspection and re-driving.
5. **No Built-in Audit Trail**: Compliance and debugging require knowing who triggered what, with what permissions, and when. FlowForge enforces structured Role-Based Access Control (RBAC) and records an immutable log of workflow runs.

---

## Who It's For

FlowForge is built for developers, system operators, and teams who need reliable background task automation—such as batch data pipelines, external HTTP webhook orchestrations, automated report generation, and asynchronous maintenance tasks—and want a production-ready API and web dashboard out of the box rather than building custom queue infrastructure from scratch.

---

## Key Features

Every feature in FlowForge is backed by concrete implementations in the codebase:

- **JWT Authentication & Role-Based Access Control (RBAC)**: Secure access token and refresh token rotation with bcrypt password hashing. Fine-grained roles (`admin`, `member`, `viewer`) control access to workflow management, job execution, and system-wide administration.
- **Declarative Workflow Definitions**: Workflows are configured as ordered lists of tasks, supporting built-in execution handlers (`log_message`, `sleep`, and `http_call`) with custom step configurations and individual retry policies.
- **Job Triggering & Step Orchestration**: Jobs unpack workflow definitions into discrete sequential database tasks (`pending` $\rightarrow$ `running` $\rightarrow$ `completed` / `failed`), automatically chaining execution from one step to the next upon success.
- **Resilient Retries with Exponential Backoff**: Tasks handle transient errors automatically. If a step fails, the worker calculates an exponential backoff delay based on the attempt count and schedules a retry using Celery countdown timers without blocking the worker process.
- **Dead-Letter Handling (DLQ)**: Tasks that exhaust their maximum configured retry attempts are cleanly terminated and archived into a dedicated `dead_letter_tasks` table along with the input payload, error diagnostics, and attempt counts for easy triage and re-execution.
- **Priority-Tiered Execution**: Jobs accept an integer priority (1–10, where lower numbers denote higher urgency). The orchestration engine routes tasks dynamically to dedicated `high`, `default`, or `low` queues, ensuring high-priority workloads jump ahead of routine tasks.
- **Responsive Web Dashboard**: A modern Next.js 16 and Tailwind CSS frontend providing authenticated views to create workflows, trigger and inspect jobs with live status polling, view step output payloads, and audit dead letters.
- **Full Docker Compose Stack**: Fully containerized multi-service environment orchestrating PostgreSQL 16, Redis 7, FastAPI backend, Celery worker, and Next.js frontend with isolated networking and health checks.
- **Automated CI/CD Pipeline**: GitHub Actions workflows run backend unit and integration tests via `pytest` (enforcing coverage thresholds) and frontend test suites via `jest` on every commit and pull request.