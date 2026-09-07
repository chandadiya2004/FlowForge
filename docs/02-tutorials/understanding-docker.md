# Tutorial: Understanding Docker in FlowForge

**What you will learn**:
- How images, containers, bridge networks, and named volumes interact in a real-world multi-service architecture.
- How Docker's embedded DNS server facilitates inter-container communication without hardcoded IP addresses.
- The critical difference between host port publishing (`ports:`) and container-only communication.
- Why named volumes guarantee data durability across container updates and restarts.
- How healthcheck-driven dependency gating (`condition: service_healthy`) prevents startup race conditions.
- A comprehensive, line-by-line operational breakdown of [infrastructure/docker-compose.yml](file:///d:/Edutation(P)/FlowForge/infrastructure/docker-compose.yml).

---

## Architectural Topology: How Docker Coordinates FlowForge

The diagram below illustrates how Docker Desktop isolates containers, mounts persistent host storage, and facilitates internal and external traffic across virtual bridge networks:

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'darkMode': true,
    'background': '#0b0f19',
    'mainBkg': '#0f172a',
    'primaryColor': '#1e293b',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#94a3b8',
    'secondaryColor': '#0f172a',
    'tertiaryColor': '#1e293b'
  }
}}%%
flowchart TB
    classDef host fill:#0b0f19,stroke:#64748b,stroke-width:1.5px,color:#f8fafc;
    classDef client fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff;
    classDef api fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#e0e7ff;
    classDef broker fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#fef2f2;
    classDef worker fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5;
    classDef volume fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#faf5ff;

    subgraph HostSystem["Physical Host Machine (Your Laptop / Server)"]
        Browser["Host Browser / Developer CLI"]:::client

        subgraph DockerBridge["Virtual Bridge Network: flowforge_network"]
            Frontend["flowforge-frontend\n(:3000 inside container)"]:::client
            Backend["flowforge-backend\n(:8000 inside container)"]:::api
            Worker["flowforge-worker\n(No Exposed Host Ports)"]:::worker
            Postgres["flowforge-postgres\n(:5432 inside container)"]:::volume
            Redis["flowforge-redis\n(:6379 inside container)"]:::broker
        end

        subgraph NamedVolumes["Host Disk Storage (Named Volumes)"]
            VolPostgres[("flowforge_postgres_data\n(Mounted to /var/lib/postgresql/data)")]:::volume
            VolRedis[("flowforge_redis_data\n(Mounted to /data)")]:::broker
        end
    end

    %% Port Forwarding
    Browser -->|"Port Tunnel :3000:3000"| Frontend
    Browser -->|"Port Tunnel :8000:8000"| Backend
    Browser -.->|"Optional Debug :5432:5432"| Postgres
    Browser -.->|"Optional Debug :6379:6379"| Redis

    %% Internal DNS Resolution
    Frontend -->|"Internal DNS http://backend:8000"| Backend
    Backend -->|"Internal DNS postgres:5432"| Postgres
    Backend -->|"Internal DNS redis:6379"| Redis
    Worker -->|"Internal DNS redis:6379 (BRPOP)"| Redis
    Worker -->|"Internal DNS postgres:5432 (SQLAlchemy)"| Postgres

    %% Volume Mounts
    Postgres <-->|"Persistent ACID Writes"| VolPostgres
    Redis <-->|"Snapshot & ETA Persistence"| VolRedis

    style HostSystem fill:#090d16,stroke:#334155,stroke-width:2px,color:#f8fafc
    style DockerBridge fill:#0f172a,stroke:#38bdf8,stroke-width:2px,stroke-dasharray: 6 6,color:#e2e8f0
    style NamedVolumes fill:#0f172a,stroke:#c084fc,stroke-width:1.5px,color:#e2e8f0
```

---

## The Four Core Docker Concepts

### 1. Image vs. Container

- **An Image** is an immutable, read-only template package containing application code, runtimes, system dependencies, and configuration.
  - *Examples in FlowForge*: `postgres:16-alpine` downloaded from Docker Hub, or the custom Python image built from `backend/Dockerfile`.
- **A Container** is an active, running instance of an image. If an image is a compiled class in software design, a container is an instantiated object running in an isolated process namespace on your system.
  - *Example in FlowForge*: When Docker Compose initializes, it instantiates the backend image into a container named `flowforge-backend`. You can stop, inspect, restart, or destroy this container without altering the underlying image.

---

### 2. Virtual Bridge Networking & Service Discovery (DNS)

When services execute directly on your physical host machine without Docker, they communicate over `localhost` using designated port numbers (e.g., `localhost:5432` for Postgres, `localhost:6379` for Redis).

Within Docker, every container possesses its own isolated network namespace and its own independent loopback interface (`localhost`). Consequently:
- If `flowforge-backend` attempts to connect to `localhost:5432`, it queries PostgreSQL **inside the backend container itself**, where no database daemon is running.
- To enable inter-service communication, Docker provisions an isolated virtual **bridge network** (`flowforge_network`).
- Docker operates an **embedded DNS server** at `127.0.0.11`. Within `flowforge_network`, service names automatically resolve to the internal IP address assigned to that container.

This explains why the database connection string in [infrastructure/docker-compose.yml](file:///d:/Edutation(P)/FlowForge/infrastructure/docker-compose.yml) targets `@postgres:5432`, rather than `@localhost:5432`:

```ini
# Inside the container network, 'postgres' resolves via Docker DNS to the Postgres container IP:
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/flowforge

# Similarly, 'redis' resolves to the Redis container IP:
REDIS_URL=redis://redis:6379/0
```

#### Understanding Port Mapping (`ports:`)
You will see directives like `ports: - "8000:8000"` or `ports: - "3000:3000"`.
- This represents a **host-to-container port tunnel** (`<host_port>:<container_port>`).
- It forwards inbound network requests from your laptop (`http://localhost:3000` or `http://localhost:8000`) into the internal container bridge network.
- **Notice that `worker` does not publish any ports**: Because the Celery worker only dequeues tasks from Redis and writes state to PostgreSQL internally within `flowforge_network`, it never receives inbound HTTP traffic from your host computer.

---

### 3. Named Volumes & Data Durability

Containers are stateless and ephemeral by default. If a container writes files to its root filesystem and is subsequently deleted (`docker rm`), all newly written data is permanently lost.

A database, however, must preserve its records across container upgrades, code rebuilds, and operating system reboots. FlowForge guarantees durability using **Docker Named Volumes**:

```yaml
volumes:
  postgres_data:
    name: flowforge_postgres_data
  redis_data:
    name: flowforge_redis_data
```

Inside the PostgreSQL service definition:
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

#### Volume Lifecycle Guarantees:
- Docker mounts a persistent, managed directory on your physical hard drive into `/var/lib/postgresql/data` inside the PostgreSQL container.
- **`docker compose down`**: Halts and removes the containers and network, but **leaves named volumes completely intact**. When you launch FlowForge tomorrow, all user accounts, workflows, and historical execution records remain preserved.
- **`docker compose down -v`**: The `-v` flag instructs Docker to **permanently purge named volumes**. Use this command only when you deliberately intend to reset the database and queue to an empty state.

---

### 4. Health Checks & Startup Dependency Gating

In distributed systems, simple startup sequencing is insufficient—**service readiness** is critical.

A common architectural vulnerability in Docker Compose is relying on basic `depends_on: [postgres]`. A basic `depends_on` only verifies that Docker has spawned the container process; it does not wait for PostgreSQL to finish loading its storage engine or accepting incoming TCP connections. If the backend boots instantly, its startup migration script (`alembic upgrade head`) will crash with a connection refused error.

FlowForge eliminates this race condition using **Active Health Checks**:

#### 1. Define the health check probe in PostgreSQL:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-flowforge}"]
  interval: 5s
  timeout: 5s
  retries: 5
```
Every 5 seconds, Docker executes `pg_isready` inside the container. Once PostgreSQL responds that it is accepting queries, Docker updates the container status to `(healthy)`.

#### 2. Gate downstream services on verified health:
```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
```
Docker Compose intentionally delays booting `flowforge-backend` and `flowforge-worker` until both `postgres` and `redis` report `service_healthy`. This guarantees database migrations and Celery queue connections initialize reliably on the first attempt.

---

## Line-by-Line Breakdown of `infrastructure/docker-compose.yml`

Below is an annotated walkthrough of FlowForge's production-ready Docker Compose configuration:

```yaml
name: flowforge

services:
  # -------------------------------------------------------------
  # 1. PostgreSQL Relational System of Record
  # -------------------------------------------------------------
  postgres:
    image: postgres:16-alpine           # Minimalist Alpine Linux base image (~80MB)
    container_name: flowforge-postgres # Explicit container name for deterministic logging
    restart: unless-stopped            # Automatically restarts container on system reboot or process crash
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}         # Database superuser (defaults to postgres)
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres} # Database password
      POSTGRES_DB: ${POSTGRES_DB:-flowforge}            # Database created automatically on initial boot
    ports:
      - "5432:5432"                    # Exposes port 5432 to host for psql / pgAdmin debugging
    volumes:
      - postgres_data:/var/lib/postgresql/data # Persists relational data to named host volume
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-flowforge}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - flowforge-network              # Attaches to isolated virtual bridge network

  # -------------------------------------------------------------
  # 2. Redis In-Memory Message Broker & Result Store
  # -------------------------------------------------------------
  redis:
    image: redis:7-alpine              # Ultra-fast in-memory key-value broker
    container_name: flowforge-redis
    restart: unless-stopped
    ports:
      - "6379:6379"                    # Exposes port 6379 to host
    volumes:
      - redis_data:/data               # Persists queue backups and Celery ETA countdown metadata
    healthcheck:
      test: ["CMD", "redis-cli", "ping"] # Pings Redis; expects PONG
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - flowforge-network

  # -------------------------------------------------------------
  # 3. FastAPI Synchronous Control Plane & REST Engine
  # -------------------------------------------------------------
  backend:
    image: arpanpramanik2003/flowforge-backend:latest
    build:
      context: ../backend              # Context directory containing backend source code
      dockerfile: Dockerfile           # Compiles Python 3.11-slim runtime image
    container_name: flowforge-backend
    restart: unless-stopped
    ports:
      - "8000:8000"                    # Exposes REST API to host at http://localhost:8000
    environment:
      # Connection strings utilizing Docker DNS names 'postgres' and 'redis'
      - DATABASE_URL=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-flowforge}
      - REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
      - JWT_SECRET=${JWT_SECRET:-flowforge_default_secret_key_change_in_production}
      - JWT_EXPIRE_MINUTES=${JWT_EXPIRE_MINUTES:-60}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}
      - RETRY_BASE_DELAY_SECONDS=${RETRY_BASE_DELAY_SECONDS:-10.0}
      - RETRY_MAX_DELAY_SECONDS=${RETRY_MAX_DELAY_SECONDS:-300.0}
    depends_on:
      postgres:
        condition: service_healthy     # Delays startup until PostgreSQL is accepting SQL queries
      redis:
        condition: service_healthy     # Delays startup until Redis responds to PING
    networks:
      - flowforge-network

  # -------------------------------------------------------------
  # 4. Celery Distributed Worker Engine
  # -------------------------------------------------------------
  worker:
    image: arpanpramanik2003/flowforge-worker:latest
    build:
      context: ..                      # Context set to root so worker accesses backend models
      dockerfile: worker/Dockerfile
    container_name: flowforge-worker
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-flowforge}
      - REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
      - JWT_SECRET=${JWT_SECRET:-flowforge_default_secret_key_change_in_production}
      - RETRY_BASE_DELAY_SECONDS=${RETRY_BASE_DELAY_SECONDS:-10.0}
      - RETRY_MAX_DELAY_SECONDS=${RETRY_MAX_DELAY_SECONDS:-300.0}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - flowforge-network

  # -------------------------------------------------------------
  # 5. Next.js Administrative Web Dashboard
  # -------------------------------------------------------------
  frontend:
    image: arpanpramanik2003/flowforge-frontend:latest
    build:
      context: ../frontend
      dockerfile: Dockerfile
      args:
        # Baked into client-side JS bundle for host browser API communication
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
    container_name: flowforge-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"                    # Exposes Next.js dashboard at http://localhost:3000
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
    depends_on:
      - backend                        # Waits for backend container to spawn
    networks:
      - flowforge-network

# ---------------------------------------------------------------
# Network & Storage Volume Declarations
# ---------------------------------------------------------------
networks:
  flowforge-network:
    name: flowforge_network
    driver: bridge                     # Host-isolated software bridge network

volumes:
  postgres_data:
    name: flowforge_postgres_data      # Persistent storage volume for PostgreSQL
  redis_data:
    name: flowforge_redis_data         # Persistent storage volume for Redis
```

---

## Essential Docker Commands Reference

The following table summarizes the primary CLI commands used to manage FlowForge:

| Command | What It Accomplishes | Recommended Scenario |
| :--- | :--- | :--- |
| `docker compose -f infrastructure/docker-compose.yml up --build -d` | Compiles local Dockerfiles and launches all 5 containers in the background. | First-time setup, or after editing Python/Next.js source files. |
| `docker compose -f infrastructure/docker-compose.yml ps` | Displays container run states, mapped ports, and healthcheck status. | Routine verification that containers are `Up (healthy)`. |
| `docker compose -f infrastructure/docker-compose.yml logs -f <service>` | Streams live standard output and error logs from a specified service. | Debugging API exceptions, worker errors, or retry countdown delays. |
| `docker compose -f infrastructure/docker-compose.yml exec -it <service> <cmd>` | Executes an interactive shell command directly inside a running container. | Running ad-hoc SQL via `psql`, checking Redis via `redis-cli`, or inspecting files. |
| `docker compose -f infrastructure/docker-compose.yml restart <service>` | Cycles a single container without taking down sibling services. | Applying updated `.env` configuration variables to backend or worker. |
| `docker compose -f infrastructure/docker-compose.yml down` | Gracefully stops and destroys containers and bridge networks while preserving volume data. | Routine end of a development session. |
| `docker compose -f infrastructure/docker-compose.yml down -v` | Destroys containers, networks, **and deletes all persistent database volumes**. | Resetting the platform to a completely pristine, empty state. |

---

## Next Steps

Deepen your understanding of FlowForge's distributed architecture with these resources:

1. [Getting Started Tutorial](getting-started.md) — 5-minute practical onboarding walkthrough using Docker Compose.
2. [First Workflow Walkthrough](first-workflow-walkthrough.md) — Step-by-step tutorial building a resilient multi-step pipeline with retries and dead-letter handling.
3. [System Architecture & Topologies](../01-introduction/architecture-diagram.md) — Multi-container networking, protocol matrices, and state transitions.
4. [Technology Stack Architecture](../01-introduction/tech-stack.md) — Architectural analysis of FastAPI, Celery, PostgreSQL, Redis, and Next.js.
5. [Deploying to Production How-To](../03-how-to-guides/deploying-to-production.md) — Production container orchestration, resource limits, and secrets management.