import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_cloud_command
from tools.registry import ToolMeta, ToolCategory
from cloud.result import CloudResult
from cloud.validation import validate_empty_result


def _dump(result: CloudResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True)


@tool
def list_resources(region: str = "") -> str:
    """List all cloud resources using RMS. Returns real data from Huawei Cloud.
    RMS is a global service that only works in cn-north-4."""
    result = run_cloud_command("RMS", "ListAllResources", {"cli-region": "cn-north-4"}, cache_ttl=60)
    if result.ok and result.data and isinstance(result.data, dict):
        items = result.data.get("resources", [])
        result.item_count = len(items) if isinstance(items, list) else 0
        result.validated = True
    empty = validate_empty_result(result, "RMS", "ListAllResources")
    if empty:
        return json.dumps({"ok": True, "service": "RMS", "operation": "ListAllResources", "data": None, "item_count": 0, "message": empty})
    return _dump(result)


RESOURCES_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_resources, service="RMS", category=ToolCategory.QUERY,
        keywords=["resource", "resources", "recursos", "servicios", "activos", "all resources", "inventory", "desplegado"],
        is_read_only=True, cacheable=True, cache_ttl=60,
    ),
]
