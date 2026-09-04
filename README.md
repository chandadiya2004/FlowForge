# FlowForge

**A resilient, distributed workflow orchestration platform built for reliable background execution, automatic retries, and priority scheduling.**

[![CI](https://github.com/chandadiya2004/FlowForge/actions/workflows/ci.yml/badge.svg)](https://github.com/chandadiya2004/FlowForge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
<!-- Note: The CI badge references github.com/chandadiya2004/FlowForge and reflects the status of .github/workflows/ci.yml -->

---

FlowForge replaces fragile cron scripts and untracked background processes with structured, observable workflow pipelines. It gives teams real-time visibility into multi-step jobs, automatically recovers from transient network glitches with exponential backoff retries, and isolates poisoned tasks into a dedicated Dead-Letter Queue (DLQ) for operator triage.

---

## Features

- **JWT Authentication & RBAC**: Stateless access/refresh token rotation with `admin`, `member`, and `viewer` permissions.
- **Declarative Step Pipelines**: Define ordered workflow chains using built-in task handlers (`log_message`, `sleep`, `http_call`).
- **Priority-Tiered Scheduling**: Route urgent workflows to `high`, `default`, or `low` Celery queues over Redis.
- **Exponential Backoff Retries**: Automatically retry failed steps with non-blocking Celery countdown timers.
- **Dead-Letter Queue (DLQ)**: Capture immutable failure snapshots with error stack traces and one-click administrative requeuing.
- **Real-Time Next.js Dashboard**: Monitor live step progressions and inspect task outputs via lightweight 2-second status polling.
- **Single-Command Docker Stack**: Multi-container topology with pre-configured networking, volumes, and service health checks.
- **Automated CI Quality Gates**: 69 backend pytest tests (93% coverage) and Jest frontend suites running on every push.

---

## Preview

![FlowForge Dashboard](docs/assets/dashboard-screenshot.png)
<!-- Screenshot placeholder: Place a dashboard screenshot or GIF at docs/assets/dashboard-screenshot.png -->

---

## Quick Start

Spin up the complete five-service stack using Docker Compose:

```bash
# 1. Clone the repository
git clone https://github.com/chandadiya2004/FlowForge.git
cd FlowForge

# 2. Configure environment variables
cp infrastructure/.env.example infrastructure/.env

# 3. Build and launch all services
docker compose -f infrastructure/docker-compose.yml up --build -d
```

Once all containers report healthy, open your browser:
- **Web Dashboard**: [`http://localhost:3000`](http://localhost:3000)
- **API Health Check**: [`http://localhost:8000/health`](http://localhost:8000/health)
- **Interactive API Docs (Swagger UI)**: [`http://localhost:8000/docs`](http://localhost:8000/docs)

*For step-by-step onboarding, prerequisites, and troubleshooting, read the [Getting Started Tutorial](docs/02-tutorials/getting-started.md).*

---

## Tech Stack

FlowForge uses a modern, modular architecture:

- [FastAPI](docs/01-introduction/tech-stack.md#1-fastapi) — High-performance async REST API & Pydantic request validation
- [PostgreSQL](docs/01-introduction/tech-stack.md#3-postgresql) — ACID-compliant relational system of record
- [Redis](docs/01-introduction/tech-stack.md#4-redis) — Low-latency Celery message broker & result backend
- [Celery](docs/01-introduction/tech-stack.md#5-celery) — Distributed asynchronous task execution & priority routing
- [Next.js](docs/01-introduction/tech-stack.md#7-nextjs--typescript) — React 19 web dashboard built with TypeScript & Tailwind CSS
- [Docker Compose](docs/01-introduction/tech-stack.md#9-docker--docker-compose) — Multi-container local orchestration & networking
- [GitHub Actions](docs/01-introduction/tech-stack.md#10-github-actions) — Automated continuous integration test pipeline

*For architectural justifications and specific roles of each technology, see the [Tech Stack Reference](docs/01-introduction/tech-stack.md).*

---

## Documentation

Full documentation is available in the [`docs/`](docs/README.md) directory:

| Section | Description | Key Documents |
| :--- | :--- | :--- |
| **[1. Introduction](docs/README.md#1-introduction)** | Architectural context and high-level design. | [Overview](docs/01-introduction/overview.md) · [Tech Stack](docs/01-introduction/tech-stack.md) · [Architecture Diagram & Walkthrough](docs/01-introduction/architecture-diagram.md) |
| **[2. Tutorials](docs/README.md#2-tutorials)** | Hands-on guides from setup to first workflow. | [Getting Started](docs/02-tutorials/getting-started.md) · [First Workflow Walkthrough](docs/02-tutorials/first-workflow-walkthrough.md) · [Understanding Docker](docs/02-tutorials/understanding-docker.md) |
| **[3. How-to Guides](docs/README.md#3-how-to-guides)** | Practical recipes for everyday development. | [Running Locally Without Docker](docs/03-how-to-guides/running-locally-without-docker.md) · [Running the Test Suite](docs/03-how-to-guides/running-the-test-suite.md) · [Git & GitHub Workflow](docs/03-how-to-guides/git-and-github-workflow.md) · [Managing Dead Letters](docs/03-how-to-guides/managing-dead-letters.md) · [Deploying to Production (Stub)](docs/03-how-to-guides/deploying-to-production.md) |
| **[4. Reference](docs/README.md#4-reference)** | Detailed technical specifications. | [API Reference](docs/04-reference/api-reference.md) · [Environment Variables](docs/04-reference/environment-variables.md) · [Data Model & State Machines](docs/04-reference/data-model.md) · [CI/CD Pipeline](docs/04-reference/ci-cd-pipeline.md) |
| **[5. Explanation](docs/README.md#5-explanation)** | Deep dives into architectural trade-offs. | [Auth & RBAC](docs/05-explanation/auth-and-rbac.md) · [Job Lifecycle & Orchestration](docs/05-explanation/job-lifecycle-and-orchestration.md) · [Retry & Dead-Letter Strategy](docs/05-explanation/retry-and-dead-letter-strategy.md) · [Priority Queue Design](docs/05-explanation/priority-queue-design.md) · [Design Decisions & Trade-offs](docs/05-explanation/design-decisions-and-tradeoffs.md) |
| **[6. Project](docs/README.md#6-project)** | Delivery status, backlog, and FAQ. | [Project Roadmap](docs/06-project/roadmap.md) · [Future Scope](docs/06-project/future-scope.md) · [FAQ](docs/06-project/faq.md) |

---

## Project Structure

```text
FlowForge/
├── backend/         # FastAPI application, SQLAlchemy models, and Alembic migrations
├── frontend/        # Next.js 16 dashboard (React 19, TypeScript, Tailwind CSS)
├── worker/          # Celery background worker, task handlers, and priority routing
├── infrastructure/  # Docker Compose files, container configs, and environment templates
└── docs/            # Complete documentation suite, tutorials, and architectural references
```

---

## Project Status

FlowForge is actively developed. Current milestone status according to the [Roadmap](docs/06-project/roadmap.md):

- **Milestones 1–10 (Complete)**: Core skeleton, JWT/RBAC auth, CRUD models, Celery/Redis async plumbing, execution engine, retry & dead-lettering, priority queues, Next.js dashboard, Docker Compose stack, and CI test pipeline.
- **Documentation Suite (Complete)**: Comprehensive technical documentation across all modules.
- **Milestone 11 (Planned)**: Production cloud deployment & infrastructure provisioning.
- **Milestone 12 (Planned)**: High-concurrency load testing & worker benchmarking.

---

## Contributing

Contributions are welcome! Please review our [Contribution Guidelines](CONTRIBUTING.md) and the [Git & GitHub Workflow Guide](docs/03-how-to-guides/git-and-github-workflow.md) before submitting a Pull Request.

---

## License

This project is licensed under the terms of the [MIT License](LICENSE).
