"""
JTech Tally Bridge - Retry utility

Provides a decorator that retries a function on transient failures.
Useful for HTTP calls to TallyPrime which can occasionally time out.
"""

import functools
import time
from collections.abc import Callable

from config.logging_config import get_logger

log = get_logger(__name__)


def retry(
    attempts=3,
    delay=2.0,
    backoff=2.0,
    exceptions=(Exception,),
):
    """
    Retry decorator.

    Args:
        attempts: Maximum number of attempts (including the first).
        delay: Initial delay between attempts, in seconds.
        backoff: Multiplier applied to delay after each failure.
        exceptions: Tuple of exception types to catch.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exc = None

            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == attempts:
                        log.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            attempts,
                            exc,
                        )
                        raise
                    log.warning(
                        "%s attempt %d/%d failed: %s -- retrying in %.1fs",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                        current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            raise last_exc  # pragma: no cover

        return wrapper

    return decorator
