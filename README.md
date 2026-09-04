<div align="center">

# ⚡ FlowForge

### **Resilient • Distributed • Observable**

**A modern background job orchestration platform featuring multi-step pipelines, tiered priority scheduling, automated exponential backoff retries, and dead-letter isolation.**

<br />

[![CI Build](https://img.shields.io/github/actions/workflow/status/chandadiya2004/FlowForge/ci.yml?branch=main&style=flat-square&logo=github-actions&logoColor=white&label=CI%20Build)](https://github.com/chandadiya2004/FlowForge/actions/workflows/ci.yml)
[![Docker Hub](https://img.shields.io/badge/Docker_Hub-arpanpramanik2003-blue?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/u/arpanpramanik2003)
[![Tests Passing](https://img.shields.io/badge/tests-69%20passed-success?style=flat-square&logo=pytest&logoColor=white)](docs/03-how-to-guides/running-the-test-suite.md)
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen?style=flat-square)](docs/04-reference/ci-cd-pipeline.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)

<br />

<!-- Tech Stack Badges -->
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](docs/01-introduction/tech-stack.md#1-fastapi)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](docs/01-introduction/tech-stack.md#5-celery)
[![Redis](https://img.shields.io/badge/Redis_7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](docs/01-introduction/tech-stack.md#4-redis)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](docs/01-introduction/tech-stack.md#3-postgresql)
[![Next.js](https://img.shields.io/badge/Next.js_16-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](docs/01-introduction/tech-stack.md#7-nextjs--typescript)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](docs/01-introduction/tech-stack.md#7-nextjs--typescript)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](docs/01-introduction/tech-stack.md#8-tailwind-css)
[![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](docs/01-introduction/tech-stack.md#9-docker--docker-compose)

<br />

[📖 Explore Documentation](docs/README.md) • [🚀 Getting Started](docs/02-tutorials/getting-started.md) • [🏛️ Architecture](docs/01-introduction/architecture-diagram.md) • [📡 API Reference](docs/04-reference/api-reference.md) • [🗺️ Roadmap](docs/06-project/roadmap.md)

</div>

<br />

---

## 💡 What is FlowForge?

Running background tasks with unmanaged shell scripts or naive cron jobs creates blind spots, silent failures, and queue bottlenecks. 

**FlowForge** provides an observable, production-grade orchestration engine where workflows are defined as ordered step pipelines, dispatched asynchronously across **priority queues**, retried automatically with **exponential backoff**, and isolated into a **Dead-Letter Queue (DLQ)** upon permanent failure. With a dedicated **Next.js 16 dashboard** and **FastAPI backend**, operators gain real-time visibility into every execution run.

---

## ✨ Key Features

- 🔐 **JWT Authentication & RBAC**: Stateless access/refresh token rotation with `admin`, `member`, and `viewer` permissions.
- ⛓️ **Declarative Step Pipelines**: Define multi-step workflows using built-in task handlers (`log_message`, `sleep`, `http_call`).
- 🚦 **Priority-Tiered Scheduling**: Urgent workloads automatically route to `high`, `default`, or `low` Celery queues over Redis.
- 🔁 **Exponential Backoff Retries**: Transient task errors trigger scheduled retry countdowns without blocking worker concurrency.
- ☠️ **Dead-Letter Queue (DLQ)**: Exhausted tasks capture full diagnostic snapshots (input data, error traces) with one-click administrative requeuing.
- 📊 **Real-Time Next.js Dashboard**: Monitor live step progressions and inspect outputs with non-blocking 2-second client polling.
- 🐳 **Pre-Built Docker Hub Images**: Pull verified production images directly from [`arpanpramanik2003/flowforge-*`](https://hub.docker.com/u/arpanpramanik2003).
- 🧪 **Continuous Integration**: Automated pytest, jest, and multi-image publishing to Docker Hub on every verified commit.

---

## 🖥️ Preview

![FlowForge Dashboard](docs/assets/dashboard-screenshot.png)
<!-- Screenshot placeholder: Place a dashboard screenshot or GIF at docs/assets/dashboard-screenshot.png -->

---

## ⚡ Quick Start: Running on Any Machine

You can run FlowForge immediately on any machine with Docker Desktop installed:

### Option A: Run Pre-Built Docker Hub Images (Fastest — Ready in 30s)
No compilers, Python, or Node.js required. Pulls official published images directly from Docker Hub:

```bash
# 1. Clone repo and enter directory
git clone https://github.com/chandadiya2004/FlowForge.git
cd FlowForge

# 2. Configure environment template
cp infrastructure/.env.example infrastructure/.env

# 3. Launch the pre-built stack
docker compose -f docker-compose.prod.yml up -d
```

### Option B: Build from Source (For Local Code Development)
```bash
docker compose -f infrastructure/docker-compose.yml up --build -d
```

Once running, access the services:

| Service | Endpoint | Purpose |
| :--- | :--- | :--- |
| **Web Dashboard** | [`http://localhost:3000`](http://localhost:3000) | Next.js workflow & job management UI |
| **Backend REST API** | [`http://localhost:8000`](http://localhost:8000) | FastAPI application entry point |
| **Interactive API Docs** | [`http://localhost:8000/docs`](http://localhost:8000/docs) | Swagger UI for exploring and testing endpoints |
| **Health Check** | [`http://localhost:8000/health`](http://localhost:8000/health) | Container & monitoring liveness probe |

> [!TIP]
> For step-by-step onboarding, account registration, and troubleshooting, read the **[Getting Started Tutorial](docs/02-tutorials/getting-started.md)**.

---

## 🛠️ Tech Stack Architecture

FlowForge combines modern Python backend tooling with a reactive TypeScript frontend:

| Component | Technology | Primary Role in FlowForge |
| :--- | :--- | :--- |
| **API Control Plane** | [FastAPI](docs/01-introduction/tech-stack.md#1-fastapi) | Async ASGI REST API with Pydantic request validation and OpenAPI schemas |
| **Database** | [PostgreSQL 16](docs/01-introduction/tech-stack.md#3-postgresql) | ACID-compliant relational system of record (workflows, jobs, tasks, DLQ) |
| **ORM & Migrations** | [SQLAlchemy + Alembic](docs/01-introduction/tech-stack.md#2-sqlalchemy--alembic) | Declarative data modeling and automated schema version migrations |
| **Message Broker** | [Redis 7](docs/01-introduction/tech-stack.md#4-redis) | In-memory message transport and task result backend for Celery |
| **Execution Engine** | [Celery 5](docs/01-introduction/tech-stack.md#5-celery) | Distributed asynchronous worker runtime with tiered queue routing |
| **Frontend Dashboard** | [Next.js 16 (React 19)](docs/01-introduction/tech-stack.md#7-nextjs--typescript) | Modern web UI built with TypeScript and [Tailwind CSS](docs/01-introduction/tech-stack.md#8-tailwind-css) |
| **Containerization** | [Docker Compose](docs/01-introduction/tech-stack.md#9-docker--docker-compose) | Multi-container orchestration, isolated bridge networking, and volumes |
| **Continuous Integration** | [GitHub Actions](docs/01-introduction/tech-stack.md#10-github-actions) | Automated linting, test suites (`pytest`, `jest`), and Docker image builds |

*For in-depth justifications and architectural trade-offs, read the [Tech Stack Documentation](docs/01-introduction/tech-stack.md).*

---

## 📚 Documentation Directory

Complete documentation is organized in the [`docs/`](docs/README.md) directory:

```
docs/
├── 01-introduction/  → Architecture diagrams, high-level overview, and tech stack justifications
├── 02-tutorials/     → Guided walkthroughs for onboarding, first workflow runs, and Docker concepts
├── 03-how-to-guides/ → Running without Docker, executing tests, Git workflows, and managing DLQ
├── 04-reference/     → REST API contracts, environment variables, ER schemas, and CI/CD pipelines
├── 05-explanation/   → Deep dives into RBAC, sequential orchestration, retries, and priority queues
└── 06-project/       → Milestone roadmap, future feature backlog, and frequently asked questions
```

| Section | Key Documents |
| :--- | :--- |
| **[1. Introduction](docs/README.md#1-introduction)** | [Overview](docs/01-introduction/overview.md) • [Tech Stack](docs/01-introduction/tech-stack.md) • [Architecture Diagram & Walkthrough](docs/01-introduction/architecture-diagram.md) |
| **[2. Tutorials](docs/README.md#2-tutorials)** | [Getting Started](docs/02-tutorials/getting-started.md) • [First Workflow Walkthrough](docs/02-tutorials/first-workflow-walkthrough.md) • [Understanding Docker](docs/02-tutorials/understanding-docker.md) |
| **[3. How-to Guides](docs/README.md#3-how-to-guides)** | [Running Locally Without Docker](docs/03-how-to-guides/running-locally-without-docker.md) • [Running the Test Suite](docs/03-how-to-guides/running-the-test-suite.md) • [Git & GitHub Workflow](docs/03-how-to-guides/git-and-github-workflow.md) • [Managing Dead Letters](docs/03-how-to-guides/managing-dead-letters.md) • [Deploying to Production](docs/03-how-to-guides/deploying-to-production.md) |
| **[4. Reference](docs/README.md#4-reference)** | [API Reference](docs/04-reference/api-reference.md) • [Environment Variables](docs/04-reference/environment-variables.md) • [Data Model & State Machines](docs/04-reference/data-model.md) • [CI/CD Pipeline](docs/04-reference/ci-cd-pipeline.md) |
| **[5. Explanation](docs/README.md#5-explanation)** | [Auth & RBAC](docs/05-explanation/auth-and-rbac.md) • [Job Lifecycle & Orchestration](docs/05-explanation/job-lifecycle-and-orchestration.md) • [Retry & Dead-Letter Strategy](docs/05-explanation/retry-and-dead-letter-strategy.md) • [Priority Queue Design](docs/05-explanation/priority-queue-design.md) • [Design Decisions & Trade-offs](docs/05-explanation/design-decisions-and-tradeoffs.md) |
| **[6. Project](docs/README.md#6-project)** | [Project Roadmap](docs/06-project/roadmap.md) • [Future Scope](docs/06-project/future-scope.md) • [FAQ](docs/06-project/faq.md) |

---

## 📁 Repository Structure

```text
FlowForge/
├── backend/         # FastAPI REST application, SQLAlchemy models, and Alembic migrations
├── frontend/        # Next.js 16 client dashboard (React 19, TypeScript, Tailwind CSS)
├── worker/          # Celery background worker, task handlers, and priority queue routing
├── infrastructure/  # Docker Compose orchestration, container configs, and .env templates
└── docs/            # Full documentation suite, architecture diagrams, and tutorials
```

---

## 📌 Project Status & Roadmap

Current milestone status from the **[Project Roadmap](docs/06-project/roadmap.md)**:

- ✅ **Milestones 1–10 (Completed)**: Core skeleton, JWT/RBAC auth, CRUD models, Celery/Redis plumbing, execution engine, retry & dead-lettering, priority queues, Next.js dashboard, Docker Compose stack, and automated CI test pipeline.
- ✅ **Documentation Suite (Completed)**: 23 comprehensive, verified technical documentation guides.
- ⏳ **Milestone 11 (Planned)**: Production cloud deployment & container registry publishing.
- ⏳ **Milestone 12 (Planned)**: High-concurrency load testing & worker performance benchmarking.

---

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome! Please review our **[Contribution Guidelines](CONTRIBUTING.md)** and the **[Git & GitHub Workflow Guide](docs/03-how-to-guides/git-and-github-workflow.md)** before submitting a Pull Request.

---

## 📄 License

Distributed under the terms of the **[MIT License](LICENSE)**.
