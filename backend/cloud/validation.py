import json
import re
from typing import Any

from cloud.result import CloudResult
from config.logging import get_logger

logger = get_logger("cloud.validation")

_EMPTY_COLLECTION_KEYS = {
    "servers", "vpcs", "subnets", "security_groups", "publicips",
    "loadbalancers", "listeners", "pools", "members", "resources",
    "bill_sums", "delegated_subnets", "routers",
    "instances", "dataStores", "flavors", "images", "backups",
}

_COUNT_KEYS = {
    "total", "count", "total_count", "item_count",
}

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def _count_items(data: Any) -> int:
    if data is None:
        return 0
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in _EMPTY_COLLECTION_KEYS:
            val = data.get(key)
            if isinstance(val, list):
                return len(val)
        for key in _COUNT_KEYS:
            val = data.get(key)
            if isinstance(val, int):
                return val
        return 1
    return 1 if data else 0


def validate_cloud_response(result: CloudResult) -> CloudResult:
    result.validated = True

    if not result.ok:
        logger.warning(
            "Cloud response error",
            extra={"structured_extra": {
                "service": result.service,
                "operation": result.operation,
                "error": result.error,
            }},
        )
        return result

    if result.data is None:
        result.item_count = 0
        return result

    if isinstance(result.data, dict):
        error_msg = result.data.get("error_msg") or result.data.get("message")
        error_code = result.data.get("error_code") or result.data.get("code")
        if error_msg and error_code:
            result.ok = False
            result.error = f"{error_code}: {error_msg}"
            logger.warning(
                "Cloud API error in response body",
                extra={"structured_extra": {
                    "service": result.service,
                    "operation": result.operation,
                    "error_code": error_code,
                    "error_msg": error_msg,
                }},
            )
            return result

    result.item_count = _count_items(result.data)

    logger.info(
        "Cloud response validated",
        extra={"structured_extra": {
            "service": result.service,
            "operation": result.operation,
            "ok": result.ok,
            "item_count": result.item_count,
        }},
    )
    return result


def validate_empty_result(result: CloudResult, service: str, operation: str) -> str:
    if not result.ok:
        return f"Error consulting {service}: {result.error}"

    if result.item_count == 0 or result.data is None:
        return f"No se encontraron recursos de {service} para la operación {operation}."

    return ""


_TRUNCATION_MARKER = "...[Output truncated to"


def _repair_truncated_json(json_str: str) -> Any | None:
    marker_pos = json_str.find(_TRUNCATION_MARKER)
    if marker_pos == -1:
        return None
    truncated = json_str[:marker_pos].rstrip()
    for trim_suffix in (",", ",\n", "\n"):
        if truncated.endswith(trim_suffix):
            truncated = truncated[: -len(trim_suffix)]
            break
    open_braces = 0
    open_brackets = 0
    in_string = False
    escape_next = False
    for ch in truncated:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            open_braces += 1
        elif ch == "}":
            open_braces -= 1
        elif ch == "[":
            open_brackets += 1
        elif ch == "]":
            open_brackets -= 1
    if open_braces < 0 or open_brackets < 0:
        return None
    repaired = truncated + "]" * open_brackets + "}" * open_braces
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    if truncated.startswith("["):
        last_item_end = truncated.rfind("}")
        if last_item_end > 0:
            candidate = truncated[: last_item_end + 1] + "]" * open_brackets + "}" * open_braces
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
    elif truncated.startswith("{"):
        for key in ("resources", "servers", "vpcs", "subnets", "instances", "data"):
            array_key_pos = truncated.rfind(f'"{key}"')
            if array_key_pos == -1:
                continue
            last_item_end = truncated.rfind("}")
            if last_item_end > array_key_pos:
                after_item = truncated[last_item_end + 1 :].lstrip()
                if after_item.startswith(","):
                    truncated_clean = truncated[: last_item_end + 1]
                else:
                    truncated_clean = truncated[: last_item_end + 1]
                open_b = 0
                open_br = 0
                in_s = False
                esc = False
                for ch in truncated_clean:
                    if esc:
                        esc = False
                        continue
                    if ch == "\\":
                        esc = True
                        continue
                    if ch == '"':
                        in_s = not in_s
                        continue
                    if in_s:
                        continue
                    if ch == "{":
                        open_b += 1
                    elif ch == "}":
                        open_b -= 1
                    elif ch == "[":
                        open_br += 1
                    elif ch == "]":
                        open_br -= 1
                candidate = truncated_clean + "]" * max(open_br, 0) + "}" * max(open_b, 0)
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
    return None


def extract_json_from_koocli(raw: str) -> Any | None:
    if not raw:
        return None
    cleaned = raw.replace("Success:\n", "", 1)
    cleaned = _ANSI_RE.sub("", cleaned)
    start = cleaned.find("{")
    start_list = cleaned.find("[")
    if start_list != -1 and (start_list < start or start == -1):
        start = start_list
    if start == -1:
        return None
    json_str = cleaned[start:]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        repaired = _repair_truncated_json(json_str)
        if repaired is not None:
            logger.info("Truncated JSON repaired successfully")
            return repaired
        return None


def extract_id(result: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, result)
        if match:
            return match.group(1)
    return ""
