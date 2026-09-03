import logging
import time
from typing import Any, Callable
import httpx

logger = logging.getLogger("flowforge.worker.tasks")
logger.setLevel(logging.INFO)


def handle_log_message(input_data: dict[str, Any]) -> dict[str, Any]:
    """Handler for 'log_message' task type."""
    message = input_data.get("message", "")
    logger.info("[Task log_message]: %s", message)
    return {"logged": message}


def handle_sleep(input_data: dict[str, Any]) -> dict[str, Any]:
    """Handler for 'sleep' task type."""
    seconds = float(input_data.get("seconds", 1))
    logger.info("[Task sleep]: Sleeping for %s seconds", seconds)
    time.sleep(seconds)
    return {"slept": seconds}


def handle_http_call(input_data: dict[str, Any]) -> dict[str, Any]:
    """Handler for 'http_call' task type.
    
    Raises an HTTPStatusError or RequestError if the request fails or is not 2xx.
    """
    url = input_data.get("url")
    if not url:
        raise ValueError("Missing required 'url' parameter for http_call task")

    method = input_data.get("method", "GET").upper()
    headers = input_data.get("headers", {})
    body = input_data.get("body")
    timeout = float(input_data.get("timeout", 10.0))

    logger.info("[Task http_call]: %s %s", method, url)
    with httpx.Client(timeout=timeout) as client:
        response = client.request(method=method, url=url, headers=headers, json=body if isinstance(body, dict) else None, content=body if isinstance(body, (str, bytes)) else None)
        response.raise_for_status()
        return {
            "status_code": response.status_code,
            "body": response.text[:1000],
        }


# Task handler registry mapping type strings to functions
TASK_REGISTRY: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "log_message": handle_log_message,
    "sleep": handle_sleep,
    "http_call": handle_http_call,
}


def get_handler(task_type: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Retrieve handler function for a given task type.
    
    Raises:
        ValueError: If task_type is unknown.
    """
    if task_type not in TASK_REGISTRY:
        supported = ", ".join(repr(k) for k in TASK_REGISTRY.keys())
        raise ValueError(
            f"Unsupported task type: '{task_type}'. Available task types: [{supported}]"
        )
    return TASK_REGISTRY[task_type]
