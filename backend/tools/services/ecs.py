import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_koocli_json


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True)


@tool
def list_ecs(region: str = "") -> str:
    """List ECS instances in a region."""
    params = {"cli-region": region} if region else None
    result = run_koocli_json("ECS", "ListCloudServers", params)
    payload = {
        "ok": result.ok,
        "service": "ECS",
        "operation": "ListCloudServers",
        "data": result.data if result.ok else None,
        "error": result.error,
    }
    return _dump(payload)


@tool
def describe_ecs(server_id: str, region: str = "") -> str:
    """Describe a single ECS instance by server_id."""
    params = {"server_id": server_id}
    if region:
        params["cli-region"] = region
    result = run_koocli_json("ECS", "ShowServer", params)
    payload = {
        "ok": result.ok,
        "service": "ECS",
        "operation": "ShowServer",
        "data": result.data if result.ok else None,
        "error": result.error,
    }
    return _dump(payload)
