from typing import Any

from schemas.loader import SchemaLoader


def validate_required_params(
    service: str,
    operation: str,
    provided_params: dict[str, Any] | None,
    loader: SchemaLoader | None = None,
) -> tuple[bool, list[str]]:
    if loader is None:
        loader = SchemaLoader()

    schema = loader.load_service(service)
    if not schema:
        return False, [f"Service '{service}' not found in schema"]

    op_schema = loader.find_operation(schema, operation)
    if not op_schema:
        return False, [f"Operation '{operation}' not found in '{service}'"]

    required, _, _ = loader.get_operation_params(op_schema)

    if not required:
        return True, []

    if provided_params is None:
        provided_params = {}

    missing = []
    for p in required:
        name = p["name"]
        if name not in provided_params:
            missing.append(f"--{name} (type={p['type']})")

    return len(missing) == 0, missing
