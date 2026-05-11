import json
import time
from typing import Any

from config.logging import get_logger
from config.settings import get_settings
from koocli.executor import execute_koocli
from cloud.result import CloudResult
from cloud.validation import extract_json_from_koocli, validate_cloud_response
from cloud.cache import CloudCache

logger = get_logger("tools.koocli_runner")

_settings = get_settings()


def run_cloud_command(
    service: str,
    operation: str,
    params: dict[str, Any] | None = None,
    use_cache: bool = True,
    cache_ttl: int | None = None,
) -> CloudResult:
    cache = CloudCache.instance(
        ttl=cache_ttl or _settings.cache_ttl_seconds,
        max_entries=_settings.cache_max_entries,
    )
    cache_key = CloudCache.make_key(service, operation, params)

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            cached.from_cache = True
            logger.debug("Cache hit", extra={"structured_extra": {
                "service": service, "operation": operation,
            }})
            return cached

    started = time.perf_counter()
    output = execute_koocli(service, operation, params)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    if output.startswith("Error"):
        result = CloudResult.from_error(service, operation, output, elapsed_ms)
        logger.warning("KooCLI error", extra={"structured_extra": {
            "service": service, "operation": operation, "elapsed_ms": elapsed_ms,
        }})
        return result

    parsed = extract_json_from_koocli(output)
    if parsed is None:
        result = CloudResult.from_error(service, operation, "Non-JSON response from KooCLI", elapsed_ms)
        result.raw = output
        return result

    result = CloudResult.success(service, operation, parsed, raw=output, elapsed_ms=elapsed_ms)
    result = validate_cloud_response(result)

    if use_cache and result.ok:
        cache.set(cache_key, result)

    logger.info("KooCLI ok", extra={"structured_extra": {
        "service": service, "operation": operation,
        "elapsed_ms": elapsed_ms, "items": result.item_count,
    }})

    return result
