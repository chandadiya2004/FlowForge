# Priority Queue Design

In background processing systems, all tasks are not created equal. A customer-facing webhook or transactional alert must execute with urgency, whereas a bulk reporting job or data synchronization can safely tolerate delays under heavy system load.

This document explains why FlowForge implements priority routing using **three tiered Celery queues (`high`, `default`, `low`) over Redis**, the engineering trade-offs of this design, and why heavier message brokers like RabbitMQ were bypassed.

---

## 1. Why Tiered Queues Over Fine-Grained Numeric Priority

On the `Job` model, priority is represented as an integer from `1` to `10` (where `1` denotes highest urgency, and `10` denotes lowest).

A naive design would attempt to pass this numeric integer directly to the message broker, expecting tasks with priority `1` to always pop off the queue ahead of priority `2`.

However, **our message broker is Redis**.

### The Redis Broker Reality
- Redis is an in-memory data store with primitive list and set data structures. It does not have native AMQP-style priority queue primitives.
- While Celery provides an experimental `priority_steps` option for Redis, it operates by fabricating multiple Redis lists behind the scenes (e.g. `celery\x06\x161`, `celery\x06\x162`). Under load or across multiple workers, this implementation can suffer from message reordering bugs and unpredictable prefetching behavior.
- In contrast, **discrete named queues** (`high`, `default`, `low`) are first-class, rock-solid primitives in both Redis and Celery.

### The FlowForge Priority Mapping (`app/core/queue_routing.py`)

FlowForge maps integer priorities into three explicit queues:

```python
HIGH_QUEUE = "high"
DEFAULT_QUEUE = "default"
LOW_QUEUE = "low"

def get_queue_for_priority(priority: int) -> str:
    if 1 <= priority <= 3:
        return HIGH_QUEUE
    elif 4 <= priority <= 7:
        return DEFAULT_QUEUE
    elif 8 <= priority <= 10:
        return LOW_QUEUE
    return DEFAULT_QUEUE
```

When Celery starts, the worker process is instructed to consume from all three queues in strict priority order:
```bash
celery -A celery_app.celery_app worker -Q high,default,low
```

Because Celery inspects queues in the order they are declared in the `-Q` argument, a worker looking for its next task will always check the `high` queue first, drain it completely, proceed to `default`, and only process `low` when no higher-priority tasks are waiting.

---

## 2. What Was Traded Away: Honest Limitations

While tiered queues provide reliable execution under load, this approach entails two major trade-offs:

### 1. Coarse Granularity
Within a single tier, priority is First-In, First-Out (FIFO). A task with priority `1` and a task with priority `3` both land in the `"high"` queue. If the priority `3` task arrived 10 milliseconds earlier, it will execute first. There is no sub-tier reordering.

### 2. "Per Worker Idle Cycle" Enforcement (No Hard Real-Time Preemption)
Celery is a cooperative task consumer, not a preemptive operating system kernel:
- If all worker concurrency processes are currently busy executing long-running tasks (for example, three `sleep` tasks from the `low` queue running for 60 seconds), an incoming `high` priority task cannot preempt or pause the running low-priority tasks.
- The `high` priority task must wait in Redis until at least one worker process finishes its current task and becomes idle.

---

## 3. The Alternative Considered: RabbitMQ

If strict, granular numeric priority (0–255) is an absolute hard requirement, the industry-standard broker is **RabbitMQ**:
- RabbitMQ natively implements `x-max-priority` integer priority ordering within a single queue. Tasks with higher priority immediately jump to the head of the line, regardless of submission time.

### Why RabbitMQ Was Omitted for FlowForge
1. **Operational Footprint**: RabbitMQ requires an Erlang runtime, dedicated cluster management, disk-backed persistent storage, and significantly higher baseline memory consumption.
2. **Dual-Dependency Redundancy**: Celery requires both a message broker (to pass messages) and a **result backend** (to query task status and results). RabbitMQ is an excellent broker, but it makes a poor result backend (it generates transient result queues that create significant broker overhead).
3. **Architectural Economy**: FlowForge already required Redis to serve as Celery's result backend. By utilizing Redis as both broker and result backend, we eliminated an entire stateful database engine from our infrastructure stack (`infrastructure/docker-compose.yml`), drastically simplifying local development, CI pipelines, and resource requirements.