# FlowForge Documentation

Welcome to the FlowForge documentation. FlowForge is a resilient, distributed workflow orchestration platform built with FastAPI, Celery, Redis, PostgreSQL, and Next.js.

Use this documentation index to navigate the project's guides, tutorials, architecture references, and technical specifications.

---

## Table of Contents

### 1. Introduction
High-level architectural context, tech stack breakdown, and system diagrams.
- [Overview](01-introduction/overview.md) — High-level overview of FlowForge, its core value proposition, and workflow orchestration capabilities.
- [Tech Stack](01-introduction/tech-stack.md) — Breakdown of technologies, libraries, and frameworks powering the backend, worker, broker, database, and frontend.
- [Architecture Diagram](01-introduction/architecture-diagram.md) — System component diagrams illustrating communication flow between Next.js, FastAPI, Celery, Redis, and PostgreSQL.

### 2. Tutorials
Step-by-step hands-on guides for onboarding and running your first workflows.
- [Getting Started](02-tutorials/getting-started.md) — Step-by-step guide to cloning, configuring, and launching the full FlowForge stack with Docker Compose.
- [First Workflow Walkthrough](02-tutorials/first-workflow-walkthrough.md) — End-to-end walkthrough creating, dispatching, and monitoring your first workflow job via the UI and API.
- [Understanding Docker](02-tutorials/understanding-docker.md) — A beginner-friendly walkthrough explaining container orchestration, services, volumes, and networking in FlowForge.

### 3. How-to Guides
Practical problem-solving recipes for everyday development and operations.
- [Running Locally Without Docker](03-how-to-guides/running-locally-without-docker.md) — Instructions for running the FastAPI backend, Celery worker, and Next.js frontend natively on a host machine.
- [Running the Test Suite](03-how-to-guides/running-the-test-suite.md) — Guide to running automated test suites, coverage reports, and linter checks for both backend (pytest) and frontend (jest).
- [Git and GitHub Workflow](03-how-to-guides/git-and-github-workflow.md) — Contributor git workflow, branch naming conventions, PR guidelines, and CI checks.
- [Managing Dead Letters](03-how-to-guides/managing-dead-letters.md) — Step-by-step instructions for inspecting, analyzing, and re-driving tasks recorded in the dead-letter queue.
- [Deploying to Production](03-how-to-guides/deploying-to-production.md) — Production deployment instructions, container hardening, and infrastructure considerations.

### 4. Reference
Technical specifications, API contracts, configuration schemas, and data structures.
- [API Reference](04-reference/api-reference.md) — Comprehensive REST API documentation detailing endpoints, request payloads, responses, and error codes.
- [Environment Variables](04-reference/environment-variables.md) — Full reference catalog of environment variables used across backend, worker, frontend, and database services.
- [Data Model](04-reference/data-model.md) — Entity-relationship schemas, database tables, constraints, and SQLAlchemy model specifications.
- [CI/CD Pipeline](04-reference/ci-cd-pipeline.md) — Technical reference for GitHub Actions workflows, test automation steps, and quality gates.

### 5. Explanation
Deep dives into architectural design patterns, trade-offs, and underlying mechanics.
- [Auth and RBAC](05-explanation/auth-and-rbac.md) — Architectural explanation of JWT token rotation, authentication lifecycle, and role-based access control.
- [Job Lifecycle and Orchestration](05-explanation/job-lifecycle-and-orchestration.md) — In-depth breakdown of DAG execution, job state transitions, and asynchronous task scheduling.
- [Retry and Dead-Letter Strategy](05-explanation/retry-and-dead-letter-strategy.md) — Resilience design detailing exponential backoff, retry limits, and dead-letter queue isolation.
- [Priority Queue Design](05-explanation/priority-queue-design.md) — Design explanation of tiered Celery queues (`high`, `default`, `low`) over Redis brokers.
- [Design Decisions and Tradeoffs](05-explanation/design-decisions-and-tradeoffs.md) — Historical and architectural decisions, trade-offs, and alternatives evaluated during development.

### 6. Project
Project management, governance, release plans, and community resources.
- [Roadmap](06-project/roadmap.md) — Timeline and milestones detailing current progress and upcoming feature releases.
- [Future Scope](06-project/future-scope.md) — Long-term technical vision, prospective integrations, and distributed scaling initiatives.
- [FAQ](06-project/faq.md) — Answers to frequently asked operational, architectural, and development questions.
