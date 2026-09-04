# Frequently Asked Questions (FAQ)

This document answers common operational, architectural, and development questions about FlowForge.

---

### 1. Why build FlowForge instead of using mature platforms like Apache Airflow, Prefect, or Temporal?
FlowForge is an end-to-end engineering project built to demonstrate the foundational concepts of distributed systems: asynchronous message brokering, tiered priority scheduling, state machine orchestration, exponential backoff retries, and dead-letter isolation. 

While enterprise platforms like Airflow or Temporal have decades of collective hardening and vast ecosystems of third-party connectors, FlowForge provides a clean, transparent, and approachable codebase where an engineer can trace every single abstraction—from the HTTP request to the Celery worker and database commit—without getting lost in layers of enterprise boilerplate.

---

### 2. Can workflow steps run in parallel?
**Not currently.** In the current release, workflows execute as strictly ordered, linear task chains (`sequence = 1, 2, 3...`). 

Each step must finish successfully before the next sequential step is dispatched. Support for arbitrary Directed Acyclic Graphs (DAGs) with concurrent branching (fan-out) and join convergence (fan-in) is planned in our [Future Scope](future-scope.md).

---

### 3. What happens if a Celery worker crashes in the middle of executing a task?
**This is an honest architectural gap in the current implementation.**

If a worker container is abruptly terminated (e.g. out-of-memory kill, host crash, or ungraceful shutdown) while executing a step:
1. The `Task` record in PostgreSQL remains marked as `"running"`.
2. Because FlowForge does not currently run an active worker heartbeat lease or background "reaper" process to identify zombie tasks, the task will not automatically transition to `failed` or re-dispatch on its own.
3. Resolving a crashed task currently requires an operator to update the task status in PostgreSQL or restart the pipeline. 

A dedicated task lease and timeout-reaper mechanism is prioritized in our reliability roadmap.

---

### 4. How do I add a new custom task type to FlowForge?
FlowForge uses an extensible **Task Registry** pattern located in `worker/tasks/registry.py`. Adding a new step type takes three simple steps:

1. **Write the handler function**:
   ```python
   def handle_send_slack(input_data: dict[str, Any]) -> dict[str, Any]:
       channel = input_data.get("channel")
       message = input_data.get("message")
       # Execute Slack API call...
       return {"delivered_to": channel, "timestamp": time.time()}
   ```
2. **Register it in `TASK_REGISTRY`**:
   ```python
   TASK_REGISTRY = {
       "log_message": handle_log_message,
       "sleep": handle_sleep,
       "http_call": handle_http_call,
       "send_slack": handle_send_slack,  # Added
   }
   ```
3. **Use it in workflow definitions**: You can now specify `"type": "send_slack"` in your workflow JSON step lists.

---

### 5. Are retried tasks guaranteed to be safe from duplicate side effects (idempotency)?
**No.** As detailed in our [Retry Strategy](../05-explanation/retry-and-dead-letter-strategy.md#3-the-honest-limitation-non-idempotent-task-handlers), task handlers are not currently guaranteed to be idempotent. 

If an external network request times out after the remote server has already processed it, FlowForge's automatic retry logic will re-execute the handler, potentially duplicating side effects. Developers implementing handlers that perform state-altering external mutations (such as charges or emails) must handle deduplication externally or supply unique transaction keys until native idempotency tokens are introduced.

---

### 6. Why does the dashboard use HTTP polling instead of WebSockets or Server-Sent Events?
FlowForge opted for **2-second HTTP polling** (`GET /jobs/{id}`) because it requires zero additional infrastructure complexity:
- No persistent socket connection tracking across scaled backend containers.
- No WebSocket connection drops or reconnection logic when client devices sleep.
- Transparent traversal through reverse proxies and enterprise corporate firewalls.

While polling introduces an average 1-second visual update delay and minor request overhead, it was the most reliable and maintainable choice for our current scale.

---

### 7. Why is viewing and requeuing dead letters restricted to administrators?
Permanently failed tasks in the Dead-Letter Queue (DLQ) often contain sensitive runtime diagnostics: raw exception stack traces, internal network URLs, or customer input payloads. 

Furthermore, requeuing a task re-opens a failed job and dispatches commands back into background worker queues. Restricting these capabilities to users with the `admin` role (`require_role("admin")`) prevents standard tenants from viewing sensitive error data or triggering unauthorized worker executions.

---

### 8. Is FlowForge production-ready today?
**It depends on your use case.**

FlowForge has a robust architectural foundation:
- Fully containerized multi-service Docker topology with health checks.
- Comprehensive automated testing (69 backend unit/integration tests with 93% coverage, 3 frontend Jest test suites).
- Complete CI pipeline validating builds and tests on every push.

However, for mission-critical enterprise workloads, FlowForge is still maturing:
- Production cloud deployment infrastructure (Milestone 11) and load testing benchmarks (Milestone 12) are pending.
- External production secrets management (e.g. AWS Secrets Manager, HashiCorp Vault) and database replication are not yet configured.
- Idempotency guarantees and DAG branching are not yet supported.

See the [Roadmap](roadmap.md) for the active delivery timeline.