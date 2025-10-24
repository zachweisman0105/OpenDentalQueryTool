"""
Retry decorator with exponential backoff and jitter.

Implements retry logic for network operations with configurable backoff strategy.
"""

import functools
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

import httpx

from opendental_query.utils.app_logger import get_logger

# Type variable for decorated function return type
T = TypeVar("T")

logger = get_logger(__name__)


def retry_with_backoff(
    max_retries: int = 5,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 32.0,
    jitter: float = 0.25,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator with exponential backoff and jitter.

    Retries on:
    - ConnectionError
    - TimeoutError
    - httpx.HTTPStatusError with 5xx status codes

    Does NOT retry on:
    - httpx.HTTPStatusError with 4xx status codes (400, 401, 403, 404)
    - Other exceptions

    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        max_delay: Maximum delay cap in seconds (default: 32.0)
        jitter: Jitter factor as percentage (default: 0.25 = ±25%)

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            delay = initial_delay

            while attempt <= max_retries:
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    # Retry on network errors
                    if attempt >= max_retries:
                        raise
                    _log_retry(func.__name__, attempt, e, delay)
                    _sleep_with_jitter(delay, jitter)
                    delay = min(delay * backoff_factor, max_delay)
                    attempt += 1
                except httpx.HTTPStatusError as e:
                    # Retry only on 5xx errors
                    if 500 <= e.response.status_code < 600:
                        if attempt >= max_retries:
                            raise
                        _log_retry(func.__name__, attempt, e, delay)
                        _sleep_with_jitter(delay, jitter)
                        delay = min(delay * backoff_factor, max_delay)
                        attempt += 1
                    else:
                        # Don't retry 4xx errors (client errors)
                        raise

            # Should never reach here, but for type safety
            raise RuntimeError("Max retries exceeded")

        return wrapper

    return decorator


def _sleep_with_jitter(delay: float, jitter: float) -> None:
    """
    Sleep with random jitter.

    Args:
        delay: Base delay in seconds
        jitter: Jitter factor (0.25 = ±25%)
    """
    jitter_amount = delay * jitter
    actual_delay = delay + random.uniform(-jitter_amount, jitter_amount)
    time.sleep(max(0, actual_delay))  # Ensure non-negative


def _log_retry(func_name: str, attempt: int, error: Exception, delay: float) -> None:
    """
    Log retry attempt with sanitized error context.

    Args:
        func_name: Name of function being retried
        attempt: Current attempt number
        error: Exception that triggered retry
        delay: Delay before next attempt
    """
    error_summary = _summarize_error(error)
    logger.warning(
        "Retrying %s after %.2fs (attempt %d): %s",
        func_name,
        delay,
        attempt + 1,
        error_summary,
    )


def _summarize_error(error: Exception) -> str:
    """Generate a concise description of retryable errors."""
    if isinstance(error, httpx.HTTPStatusError):
        try:
            status = error.response.status_code if error.response is not None else "?"
        except Exception:
            status = "?"
        try:
            request = error.request  # May raise if not set
        except Exception:
            request = None
        if request is not None:
            try:
                method = request.method
            except Exception:
                method = "?"
            try:
                url = request.url
            except Exception:
                url = "?"
        else:
            method = "?"
            url = "?"
        return f"HTTPStatusError(status={status}, method={method}, url={url})"
    return f"{type(error).__name__}({str(error)[:120]})"
