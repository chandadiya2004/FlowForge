# Understanding Docker in FlowForge

If you have used Docker Desktop to start applications with `docker compose up`, but are still fuzzy on how images, containers, networks, and volumes interact behind the scenes, this tutorial is for you.

We will use FlowForge's actual `infrastructure/docker-compose.yml` file as our real-world blueprint to explain exactly what Docker does under the hood when coordinating multi-service architectures.

---

## The Four Core Docker Concepts

### 1. Image vs. Container

- **An Image** is an immutable, read-only blueprint or template containing application code, runtimes, libraries, and environment settings.
  - Examples in FlowForge: `postgres:16-alpine` downloaded from Docker Hub, or the custom Python image built from `backend/Dockerfile`.
- **A Container** is a runnable, isolated instance of an image. If an image is a class in programming, a container is an instantiated object running as an isolated process on your computer.
  - Example in FlowForge: When Compose boots, it instantiates the image into a container named `flowforge-backend`. You can stop, start, destroy, or replicate containers without modifying the underlying image.

---

### 2. Docker Networks & Service Name DNS

When services run on your host machine without Docker, they communicate over `localhost` using distinct port numbers (e.g., `localhost:5432` for Postgres, `localhost:6379` for Redis).

Inside Docker, each container has its own private network namespace and its own internal loopback interface (`localhost`). This means:
- If `flowforge-backend` tries to connect to `localhost:5432`, it is looking for PostgreSQL **inside the backend container itself**, where no database is running.
- To allow containers to communicate, Docker provisions an internal virtual **bridge network** (`flowforge-network`).
- Docker embeds an **automatic DNS resolver**. Within the `flowforge-network`, the container name or service name resolves directly to the internal IP address of that container.

This is why the backend's `DATABASE_URL` in `docker-compose.yml` connects to `@postgres:5432`, not `@localhost:5432`:

```ini
# Inside the container network, 'postgres' resolves to the PostgreSQL container IP:
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/flowforge

# Similarly, 'redis' resolves to the Redis container IP:
REDIS_URL=redis://redis:6379/0
```

#### What `ports:` Actually Does
You will notice lines like `ports: - "8000:8000"` or `ports: - "3000:3000"`.
- This is a **host-to-container port mapping** (`host_port:container_port`).
- It creates a tunnel from your laptop/desktop into the container network so your host browser can reach `http://localhost:3000` or `http://localhost:8000`.
- Notice that `worker` does **not** expose any ports (`ports:` is absent). The worker only listens to Redis and queries Postgres from inside `flowforge-network`; external traffic from the host never needs to hit the worker directly.

---

### 3. Named Volumes: Data Persistence

Containers are ephemeral by default. If you write files inside a container's filesystem and then destroy the container (`docker rm`), those files vanish permanently.

A database, however, must retain its data across container restarts, rebuilds, and code updates. FlowForge accomplishes this using **Docker Named Volumes**:

```yaml
volumes:
  postgres_data:
    name: flowforge_postgres_data
  redis_data:
    name: flowforge_redis_data
```

Inside the `postgres` service definition:
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

#### How Volumes Work:
- Docker mounts a dedicated, managed directory on your physical host drive into `/var/lib/postgresql/data` inside the PostgreSQL container.
- **`docker compose down`**: Stops and removes the containers and network, but **leaves the volumes untouched**. When you run `docker compose up` tomorrow, your workflows, jobs, and user accounts are still there.
- **`docker compose down -v`**: The `-v` (volumes) flag explicitly instructs Docker to **destroy the named volumes**. Use this when you want a completely fresh database, but remember it permanently wipes all local data!

---

### 4. `depends_on` + `healthcheck`

In distributed systems, start order matters, but **service readiness** matters even more.

A common pitfall in Docker Compose is using a basic `depends_on: [postgres]`. A standard `depends_on` only waits for Docker to create the container process; it does not wait for PostgreSQL to finish loading its tables and start accepting connections. If the backend starts immediately, its startup script (`alembic upgrade head`) will crash with a connection refused error.

FlowForge solves this with **Active Health Checks**:

#### 1. Define the health check in PostgreSQL:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-flowforge}"]
  interval: 5s
  timeout: 5s
  retries: 5
```
Every 5 seconds, Docker runs `pg_isready` inside the Postgres container. Once the database responds that it is accepting queries, Docker marks the container status as `(healthy)`.

#### 2. Gate downstream services on that health status:
```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
```
Now, Docker Compose will deliberately pause the `backend` and `worker` containers until PostgreSQL and Redis report `service_healthy`. Only then does the backend execute database migrations and boot Uvicorn.

---

## Line-by-Line Breakdown of `infrastructure/docker-compose.yml`

Here is how FlowForge configures every service in `infrastructure/docker-compose.yml`:

```yaml
name: flowforge

services:
  # -------------------------------------------------------------
  # 1. PostgreSQL Database Service
  # -------------------------------------------------------------
  postgres:
    image: postgres:16-alpine           # Lightweight official PostgreSQL 16 image based on Alpine Linux
    container_name: flowforge-postgres # Predictable container name instead of auto-generated hash
    restart: unless-stopped            # Automatically restarts container if it crashes or Docker reboots
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}         # Database superuser (reads from .env or defaults to postgres)
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres} # Database password
      POSTGRES_DB: ${POSTGRES_DB:-flowforge}            # Database created automatically on initial startup
    ports:
      - "5432:5432"                    # Exposes port 5432 to your host (useful for pgAdmin or psql)
    volumes:
      - postgres_data:/var/lib/postgresql/data # Persists DB data outside the container
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-flowforge}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - flowforge-network              # Joins the shared internal bridge network

  # -------------------------------------------------------------
  # 2. Redis Message Broker Service
  # -------------------------------------------------------------
  redis:
    image: redis:7-alpine              # Lightweight official Redis 7 image
    container_name: flowforge-redis
    restart: unless-stopped
    ports:
      - "6379:6379"                    # Exposes port 6379 to host
    volumes:
      - redis_data:/data               # Persists queue and result data across restarts
    healthcheck:
      test: ["CMD", "redis-cli", "ping"] # Pings Redis; expects PONG
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - flowforge-network

  # -------------------------------------------------------------
  # 3. FastAPI Backend Control Plane
  # -------------------------------------------------------------
  backend:
    build:
      context: ../backend              # Build directory containing backend source code
      dockerfile: Dockerfile           # Uses backend/Dockerfile (Python 3.11-slim)
    container_name: flowforge-backend
    restart: unless-stopped
    ports:
      - "8000:8000"                    # Exposes REST API to host at http://localhost:8000
    environment:
      # Injected connection string using Docker DNS 'postgres' and 'redis'
      - DATABASE_URL=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-flowforge}
      - REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
      - JWT_SECRET=${JWT_SECRET:-flowforge_default_secret_key_change_in_production}
      - JWT_EXPIRE_MINUTES=${JWT_EXPIRE_MINUTES:-60}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}
      - RETRY_BASE_DELAY_SECONDS=${RETRY_BASE_DELAY_SECONDS:-10.0}
      - RETRY_MAX_DELAY_SECONDS=${RETRY_MAX_DELAY_SECONDS:-300.0}
    depends_on:
      postgres:
        condition: service_healthy     # Waits for PostgreSQL to accept SQL queries
      redis:
        condition: service_healthy     # Waits for Redis to respond to PING
    networks:
      - flowforge-network

  # -------------------------------------------------------------
  # 4. Celery Background Worker Service
  # -------------------------------------------------------------
  worker:
    build:
      context: ..                      # Context is repo root so worker can access shared backend models
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
  # 5. Next.js Frontend Dashboard Service
  # -------------------------------------------------------------
  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
      args:
        # Build argument baked into Next.js client bundle for browser API calls
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
    container_name: flowforge-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"                    # Exposes Next.js dashboard at http://localhost:3000
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
    depends_on:
      - backend                        # Waits for backend container to start
    networks:
      - flowforge-network

# ---------------------------------------------------------------
# Shared Network & Storage Topologies
# ---------------------------------------------------------------
networks:
  flowforge-network:
    name: flowforge_network
    driver: bridge                     # Isolated virtual bridge network on the Docker host

volumes:
  postgres_data:
    name: flowforge_postgres_data      # Persistent storage volume for PostgreSQL
  redis_data:
    name: flowforge_redis_data         # Persistent storage volume for Redis
```

---

## Essential Docker Commands Reference

Here is a reference table of the primary commands used to operate FlowForge:

| Command | What It Does | When to Use It |
| :--- | :--- | :--- |
| `docker compose -f infrastructure/docker-compose.yml up --build -d` | Builds missing/updated images and starts all 5 containers in the background (detached mode). | First time running FlowForge, or after modifying code/Dockerfiles. |
| `docker compose -f infrastructure/docker-compose.yml ps` | Displays the status and health check state of all containers in the stack. | To verify whether containers are `Up (healthy)`. |
| `docker compose -f infrastructure/docker-compose.yml logs -f <service>` | Streams live logs from a specific service (e.g. `backend` or `worker`). | When debugging API requests, task retries, or execution errors. |
| `docker compose -f infrastructure/docker-compose.yml exec -it <service> <cmd>` | Executes an interactive command inside a running container. | To run database queries (`psql`), check Redis (`redis-cli`), or inspect files. |
| `docker compose -f infrastructure/docker-compose.yml restart <service>` | Restarts a single container without restarting the rest of the stack. | To reload the backend or worker after editing local environment variables. |
| `docker compose -f infrastructure/docker-compose.yml down` | Stops and removes containers and networks while preserving volume data. | Routine end of a development session. |
| `docker compose -f infrastructure/docker-compose.yml down -v` | Stops containers, removes networks, and **destroys all persistent volumes**. | To completely wipe the database and start with a fresh slate. |