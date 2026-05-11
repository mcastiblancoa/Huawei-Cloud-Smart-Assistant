import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_cloud_command
from tools.registry import ToolMeta, ToolCategory
from cloud.result import CloudResult
from cloud.validation import validate_empty_result
from config.settings import get_settings

_PRIMARY_REGIONS = ["la-north-2", "ap-southeast-3"]


def _default_region(region: str) -> str:
    return region or get_settings().huawei_region


def _dump(result: CloudResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True)


def _merge_results(service: str, operation: str, region: str | None, key: str) -> CloudResult:
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
        merged_data = {key: all_items}
        cr = CloudResult.success(service, operation, merged_data, elapsed_ms=total_elapsed, item_count=len(all_items))
        cr.validated = True
        return cr

    if last_error:
        return CloudResult.from_error(service, operation, last_error, total_elapsed)

    return CloudResult.empty(service, operation, total_elapsed)


@tool
def list_elb(region: str = "") -> str:
    """List all ELB load balancers across regions. Returns real data from Huawei Cloud."""
    result = _merge_results("ELB", "ListLoadBalancers", region or None, "loadbalancers")
    empty = validate_empty_result(result, "ELB", "ListLoadBalancers")
    if empty:
        return json.dumps({"ok": True, "service": "ELB", "operation": "ListLoadBalancers", "data": None, "item_count": 0, "message": empty})
    return _dump(result)


@tool
def describe_elb(loadbalancer_id: str, region: str = "") -> str:
    """Describe an ELB load balancer by ID. Returns real data only."""
    region = _default_region(region)
    params = {"loadbalancer_id": loadbalancer_id, "cli-region": region}
    result = run_cloud_command("ELB", "ShowLoadBalancer", params)
    if not result.ok:
        return json.dumps({"ok": False, "service": "ELB", "error": result.error})
    return _dump(result)


ELB_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_elb, service="ELB", category=ToolCategory.QUERY,
        keywords=["elb", "load balancer", "balanceador", "loadbalancer"],
        is_read_only=True, cacheable=True, cache_ttl=30,
    ),
    ToolMeta(
        tool=describe_elb, service="ELB", category=ToolCategory.QUERY,
        keywords=["describe elb", "elb detail", "elb status"],
        is_read_only=True, cacheable=True, cache_ttl=15,
    ),
]
