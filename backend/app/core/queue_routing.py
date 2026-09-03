"""Priority queue routing configuration and helper functions for FlowForge."""

HIGH_QUEUE = "high"
DEFAULT_QUEUE = "default"
LOW_QUEUE = "low"

QUEUES = (HIGH_QUEUE, DEFAULT_QUEUE, LOW_QUEUE)


def get_queue_for_priority(priority: int) -> str:
    """Maps an integer priority (1-10, lower = more urgent) to a tiered queue name.

    Mapping:
      - 1-3  -> "high"
      - 4-7  -> "default"
      - 8-10 -> "low"
    """
    if 1 <= priority <= 3:
        return HIGH_QUEUE
    elif 4 <= priority <= 7:
        return DEFAULT_QUEUE
    elif 8 <= priority <= 10:
        return LOW_QUEUE
    else:
        # Fallback for unexpected out-of-range values
        return DEFAULT_QUEUE
