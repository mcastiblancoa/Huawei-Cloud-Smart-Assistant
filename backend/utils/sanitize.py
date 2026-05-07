import re
from typing import Any


def sanitize_string(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
    return cleaned


def sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    sanitized = {}
    for key, value in params.items():
        clean_key = sanitize_string(str(key))
        if isinstance(value, str):
            sanitized[clean_key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[clean_key] = sanitize_params(value)
        elif isinstance(value, list):
            sanitized[clean_key] = [
                sanitize_string(v) if isinstance(v, str) else
                sanitize_params(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            sanitized[clean_key] = value
    return sanitized


def validate_service_name(service: str) -> str:
    cleaned = sanitize_string(service)
    if not cleaned:
        raise ValueError("Service name cannot be empty")
    if not re.match(r'^[A-Za-z][A-Za-z0-9_-]*$', cleaned):
        raise ValueError(f"Invalid service name: {cleaned}")
    return cleaned


def validate_operation_name(operation: str) -> str:
    cleaned = sanitize_string(operation)
    if not cleaned:
        raise ValueError("Operation name cannot be empty")
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', cleaned):
        raise ValueError(f"Invalid operation name: {cleaned}")
    return cleaned
