import time
import functools
from typing import Callable, TypeVar, Any

from config.logging import get_logger

logger = get_logger("utils.retry")
T = TypeVar("T")


def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 2,
    base_delay: float = 1.0,
    *args: Any,
    **kwargs: Any,
) -> T:
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {delay:.1f}s",
                    extra={"structured_extra": {
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "delay": delay,
                        "error": str(e),
                    }},
                )
                time.sleep(delay)
    raise last_exception
