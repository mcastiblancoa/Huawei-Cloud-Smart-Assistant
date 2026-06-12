import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_cloud_command
from tools.common.table_formatter import format_resources_grouped
from tools.registry import ToolMeta, ToolCategory
from cloud.result import CloudResult
from cloud.validation import validate_empty_result


def _dump(result: CloudResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True)


@tool
def list_resources(region: str = "") -> str:
    """List all cloud resources using RMS (global inventory). Each call hits the API (no local cache).
    Note: Huawei RMS can lag a few minutes behind the live ECS/API console; for live VMs use list_ecs."""
    # Inventory must reflect the account now; RMS can lag vs ECS API but local cache must not hide deletes.
    result = run_cloud_command(
        "RMS", "ListAllResources", {"cli-region": "cn-north-4"}, use_cache=False,
    )
    if result.ok and result.data and isinstance(result.data, dict):
        items = result.data.get("resources", [])
        result.item_count = len(items) if isinstance(items, list) else 0
        result.validated = True
    empty = validate_empty_result(result, "RMS", "ListAllResources")
    if empty:
        return json.dumps({"ok": True, "service": "RMS", "operation": "ListAllResources", "data": None, "item_count": 0, "message": empty})
    items = result.data.get("resources", []) if isinstance(result.data, dict) else []
    table_md = format_resources_grouped(items)
    d = result.to_dict()
    if table_md:
        d["_table"] = table_md
    return json.dumps(d, ensure_ascii=True)


RESOURCES_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_resources, service="RMS", category=ToolCategory.QUERY,
        keywords=["resource", "resources", "recursos", "servicios", "activos", "all resources", "inventory", "desplegado"],
        is_read_only=True, cacheable=False, cache_ttl=0,
    ),
]
