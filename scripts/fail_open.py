"""Fail-open decorator for epistemic measurement functions.

Wraps functions that call external APIs or do potentially-failing measurements.
On failure or timeout, returns a standardized MeasurementResult instead of crashing.
"""

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable


@dataclass
class MeasurementResult:
    """Standardized result from a measurement function."""

    result: Any = None
    coverage: float = 0.0
    confidence: float = 0.0
    error: str | None = None
    failed_open: bool = False


def _log_failure(func_name: str, error: str) -> None:
    """Log failure to stderr as JSON."""
    entry = {
        "event": "MEASUREMENT_FAILED_OPEN",
        "function": func_name,
        "error": error,
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(entry), file=sys.stderr)


def fail_open(
    timeout: float = 30,
    fallback_value: Any = None,
) -> Callable:
    """Decorator that catches exceptions and timeouts, returning a fallback result.

    On success, returns the function's actual return value unchanged.
    On failure, returns a MeasurementResult with failed_open=True.

    Args:
        timeout: Max seconds before the function is considered timed out.
        fallback_value: Value to use as MeasurementResult.result on failure.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result_box: list[Any] = []
            error_box: list[BaseException] = []

            def target():
                try:
                    result_box.append(func(*args, **kwargs))
                except BaseException as e:
                    error_box.append(e)

            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=timeout)

            if thread.is_alive():
                error_msg = f"timeout after {timeout}s"
                _log_failure(func.__name__, error_msg)
                return MeasurementResult(
                    result=fallback_value,
                    error=error_msg,
                    failed_open=True,
                )

            if error_box:
                exc = error_box[0]
                error_msg = f"{type(exc).__name__}: {exc}"
                _log_failure(func.__name__, error_msg)
                return MeasurementResult(
                    result=fallback_value,
                    error=error_msg,
                    failed_open=True,
                )

            return result_box[0]

        return wrapper

    return decorator


def fail_open_batch(
    funcs: list[tuple[Callable, tuple, dict]],
    timeout: float = 60,
    max_workers: int = 4,
) -> list[Any]:
    """Run multiple measurements in parallel with individual fail-open semantics.

    Each entry is (callable, args, kwargs). Callables should already be
    decorated with @fail_open, or will be run bare (exceptions propagate).

    Args:
        funcs: List of (callable, args, kwargs) tuples.
        timeout: Overall timeout for the batch (individual timeouts are per-decorator).
        max_workers: Max parallel threads.

    Returns:
        List of results in the same order as input.
    """
    results: list[Any] = [None] * len(funcs)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {}
        for i, (fn, args, kwargs) in enumerate(funcs):
            future = pool.submit(fn, *args, **kwargs)
            future_to_idx[future] = i

        for future in as_completed(future_to_idx, timeout=timeout):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                func_name = funcs[idx][0].__name__
                error_msg = f"{type(e).__name__}: {e}"
                _log_failure(func_name, error_msg)
                results[idx] = MeasurementResult(
                    error=error_msg,
                    failed_open=True,
                )

    return results
