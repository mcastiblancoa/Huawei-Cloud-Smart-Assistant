import json
from typing import Any


def flatten_params(params: dict, prefix: str = "") -> list[tuple[str, str]]:
    result = []
    for key, value in params.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.extend(flatten_params(value, full_key))
        elif isinstance(value, list):
            if all(not isinstance(v, (dict, list)) for v in value):
                for i, v in enumerate(value, start=1):
                    result.append((f"{full_key}.{i}", str(v)))
            else:
                for i, v in enumerate(value, start=1):
                    if isinstance(v, dict):
                        result.extend(flatten_params(v, f"{full_key}.{i}"))
                    elif isinstance(v, list):
                        result.append((f"{full_key}.{i}", json.dumps(v, separators=(',', ':'))))
                    else:
                        result.append((f"{full_key}.{i}", str(v)))
        elif isinstance(value, str) and value.strip().startswith(('{', '[')):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    result.extend(flatten_params(parsed, full_key))
                elif isinstance(parsed, list):
                    if all(not isinstance(v, (dict, list)) for v in parsed):
                        for i, v in enumerate(parsed, start=1):
                            result.append((f"{full_key}.{i}", str(v)))
                    else:
                        for i, v in enumerate(parsed, start=1):
                            if isinstance(v, dict):
                                result.extend(flatten_params(v, f"{full_key}.{i}"))
                            else:
                                result.append((f"{full_key}.{i}", str(v)))
                else:
                    result.append((full_key, value))
            except json.JSONDecodeError:
                result.append((full_key, value))
        else:
            result.append((full_key, str(value)))
    return result


AUTO_INJECTED_PARAMS = frozenset({
    "cli-region", "cli-access-key", "cli-secret-key", "project_id", "domain_id",
})


def build_cli_args(
    service: str,
    operation: str,
    params: dict[str, Any] | None,
    ak: str,
    sk: str,
    region: str,
    project_id: str | None = None,
    domain_id: str | None = None,
) -> list[str]:
    cmd = [service, operation]

    if params:
        flat = flatten_params(params)
        for key, value in flat:
            if key in ("cli-region", "region"):
                region = value
                continue
            if key in AUTO_INJECTED_PARAMS:
                continue
            escaped = str(value).replace('"', '\\"')
            cmd.append(f'--{key}="{escaped}"')

    cmd.append(f"--cli-access-key={ak}")
    cmd.append(f"--cli-secret-key={sk}")
    cmd.append(f"--cli-region={region}")

    return cmd, region
