import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_cloud_command
from tools.registry import ToolMeta, ToolCategory
from cloud.result import CloudResult
from cloud.validation import validate_empty_result
from config.settings import get_settings

_PRIMARY_REGIONS = ["la-north-2", "ap-southeast-3", "cn-north-4"]


def _default_region(region: str) -> str:
    return region or get_settings().huawei_region


def _dump(result: CloudResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True)


def _merge_list_results(service: str, operation: str, region: str | None, key: str) -> CloudResult:
    if region:
        regions = [region]
    else:
        regions = _PRIMARY_REGIONS

    all_items = []
    total_elapsed = 0
    last_error = None
    found_data = False

    for r in regions:
        result = run_cloud_command(service, operation, {"cli-region": r}, use_cache=True)
        total_elapsed += result.elapsed_ms
        if result.ok and result.data:
            found_data = True
            items = result.data.get(key, []) if isinstance(result.data, dict) else []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item["_region"] = r
                    all_items.append(item)
        elif not result.ok:
            last_error = result.error

    if found_data or all_items:
        merged_data = {key: all_items} if key else all_items
        return CloudResult.success(service, operation, merged_data, elapsed_ms=total_elapsed, item_count=len(all_items))

    if last_error:
        return CloudResult.from_error(service, operation, last_error, total_elapsed)

    return CloudResult.empty(service, operation, total_elapsed)


@tool
def list_ecs(region: str = "") -> str:
    """List all ECS instances across regions. Returns real data from Huawei Cloud."""
    result = _merge_list_results("ECS", "ListCloudServers", region or None, "servers")
    result = _validate_and_count(result, "servers")
    empty = validate_empty_result(result, "ECS", "ListCloudServers")
    if empty:
        return json.dumps({"ok": True, "service": "ECS", "operation": "ListCloudServers", "data": None, "item_count": 0, "message": empty})
    return _dump(result)


def _validate_and_count(result: CloudResult, key: str) -> CloudResult:
    if result.ok and result.data and isinstance(result.data, dict):
        items = result.data.get(key, [])
        result.item_count = len(items) if isinstance(items, list) else 0
        result.validated = True
    return result


@tool
def describe_ecs(server_id: str, region: str = "") -> str:
    """Describe a single ECS instance by server_id. Returns real data only."""
    region = _default_region(region)
    params = {"server_id": server_id, "cli-region": region}
    result = run_cloud_command("ECS", "ShowServer", params)
    if not result.ok:
        return json.dumps({"ok": False, "service": "ECS", "error": result.error})
    return _dump(result)


@tool
def start_ecs(server_id: str, region: str = "la-north-2") -> str:
    """Start an ECS instance by server_id."""
    params = {"cli-region": region, "os-start": {"servers": [{"id": server_id}]}}
    result = run_cloud_command("ECS", "BatchStartServers", params, use_cache=False)
    return _dump(result)


@tool
def stop_ecs(server_id: str, region: str = "la-north-2") -> str:
    """Stop an ECS instance by server_id."""
    params = {"cli-region": region, "os-stop": {"servers": [{"id": server_id}]}}
    result = run_cloud_command("ECS", "BatchStopServers", params, use_cache=False)
    return _dump(result)


@tool
def reboot_ecs(server_id: str, region: str = "la-north-2") -> str:
    """Reboot an ECS instance by server_id."""
    params = {"cli-region": region, "reboot": {"servers": [{"id": server_id}]}}
    result = run_cloud_command("ECS", "BatchRebootServers", params, use_cache=False)
    return _dump(result)


ECS_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_ecs, service="ECS", category=ToolCategory.QUERY,
        keywords=["ecs", "server", "servers", "instancia", "instancias", "vm", "virtual machine"],
        is_read_only=True, cacheable=True, cache_ttl=30,
    ),
    ToolMeta(
        tool=describe_ecs, service="ECS", category=ToolCategory.QUERY,
        keywords=["describe ecs", "ecs detail", "ecs status"],
        is_read_only=True, cacheable=True, cache_ttl=15,
    ),
    ToolMeta(
        tool=start_ecs, service="ECS", category=ToolCategory.MANAGE,
        keywords=["start ecs", "encender ecs", "iniciar servidor"],
        is_read_only=False, is_destructive=False, cacheable=False,
    ),
    ToolMeta(
        tool=stop_ecs, service="ECS", category=ToolCategory.MANAGE,
        keywords=["stop ecs", "detener ecs", "parar servidor"],
        is_read_only=False, is_destructive=False, cacheable=False,
    ),
    ToolMeta(
        tool=reboot_ecs, service="ECS", category=ToolCategory.MANAGE,
        keywords=["reboot ecs", "reiniciar ecs", "restart server"],
        is_read_only=False, is_destructive=False, cacheable=False,
    ),
]
