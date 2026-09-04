# Future Scope

This document outlines planned enhancements, architectural evolutions, and backlog initiatives for FlowForge beyond the initial milestone releases. Items are categorized by architectural domain to serve as an engineering backlog.

---

## 1. Workflow Engine Capabilities

- **DAG-Based Orchestration (Fan-Out / Fan-In)**: Transition from strictly linear task chains to a true Directed Acyclic Graph (DAG) model. This will allow independent steps to execute concurrently in parallel and synchronize at downstream merge nodes.
- **Workflow Versioning**: Introduce an immutable versioning scheme (`version_id`) for workflow definitions. Triggered jobs will lock to the exact revision active at invocation, preventing mid-flight pipeline definition mutations.
- **Scheduled & Cron-Triggered Jobs**: Implement a native cron scheduler (using Celery Beat or a lightweight temporal scheduler) enabling users to schedule recurring jobs directly from the dashboard or API.
- **Visual Drag-and-Drop Workflow Builder**: Replace the raw JSON definition textarea in the frontend with an interactive node-based canvas (using React Flow) for assembling and configuring task pipelines visually.
- **Task Idempotency Keys**: Add mandatory idempotency tokens generated at job creation and passed to task handlers. This ensures retried network calls (such as payment processing or webhook dispatch) cannot execute duplicate real-world side effects.

---

## 2. Security & Access Control

- **OAuth 2.0 & Social SSO**: Support third-party single sign-on via Google, GitHub, and generic OIDC providers alongside standard email/password authentication.
- **Multi-Factor Authentication (MFA / 2FA)**: Introduce time-based one-time password (TOTP) verification using authenticator apps for enhanced account protection.
- **Automated Password Reset Flow**: Implement time-limited, cryptographically signed password reset tokens dispatched via transactional email providers (SendGrid / AWS SES).
- **Fine-Grained Permissions & Team Tenancy**: Expand beyond static `admin`/`member`/`viewer` roles into customizable team workspaces and per-workflow access control lists (e.g., execute-only vs. edit permissions).

---

## 3. Reliability & Scale

- **Native AMQP Priority Broker (RabbitMQ)**: Migrate Celery message transport from Redis to RabbitMQ if coarse tiered queues (`high`, `default`, `low`) become insufficient. This will unlock true 0–255 integer priority scheduling on a single queue.
- **Dedicated Worker Pools per Tier**: Deploy separate Celery worker deployments dedicated exclusively to the `high` priority queue. This prevents long-running low-priority tasks from saturating worker concurrency during sudden traffic surges.
- **Horizontal API Scaling & Ingress**: Document production ingress configurations (Nginx / Traefik / AWS ALB) to scale stateless FastAPI backend containers horizontally across multiple nodes.
- **PostgreSQL Read Replicas**: Direct dashboard polling and read queries to PostgreSQL read replicas, reserving the primary database instance exclusively for worker state transactions.

---

## 4. Observability & Monitoring

- **Structured JSON Logging**: Standardize application logs across FastAPI, Celery, and Uvicorn using structured JSON formats for ingestion into Elasticsearch, Datadog, or Grafana Loki.
- **Distributed Tracing (OpenTelemetry)**: Implement end-to-end tracing spanning the HTTP request, Redis message publication, Celery task pickup, and database write operations.
- **Prometheus Metrics & Grafana Dashboards**: Expose real-time operational metrics for queue latency, active worker concurrency, failure rates, and job throughput.
- **Dead-Letter Alerting**: Configure automated notification triggers (PagerDuty, Slack, email) when the accumulation rate of `dead_letter_tasks` exceeds defined operational thresholds.

---

## 5. Integrations & Platform Ecosystem

- **Webhook & Notification Handlers**: Add built-in workflow notification hooks that dispatch HTTP webhooks, Slack channel alerts, or emails upon job completion or failure.
- **First-Class Public API & Python/TypeScript SDKs**: Formalize public API keys and publish lightweight client libraries allowing external services to trigger pipelines and poll execution status programmatically.