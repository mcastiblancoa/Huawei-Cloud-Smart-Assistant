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
def list_vpcs(region: str = "") -> str:
    """List all VPCs across regions. Returns real data from Huawei Cloud."""
    result = _merge_results("VPC", "ListVpcs", region or None, "vpcs")
    empty = validate_empty_result(result, "VPC", "ListVpcs")
    if empty:
        return json.dumps({"ok": True, "service": "VPC", "operation": "ListVpcs", "data": None, "item_count": 0, "message": empty})
    return _dump(result)


@tool
def describe_vpc(vpc_id: str, region: str = "") -> str:
    """Describe a VPC by ID. Returns real data only."""
    region = _default_region(region)
    params = {"vpc_id": vpc_id, "cli-region": region}
    result = run_cloud_command("VPC", "ShowVpc", params)
    if not result.ok:
        return json.dumps({"ok": False, "service": "VPC", "error": result.error})
    return _dump(result)


@tool
def create_vpc(name: str, cidr: str = "10.0.0.0/16", region: str = "ap-southeast-3") -> str:
    """Create a VPC on Huawei Cloud."""
    params = {"cli-region": region, "vpc": {"name": name, "cidr": cidr}}
    result = run_cloud_command("VPC", "CreateVpc", params, use_cache=False)
    return _dump(result)


@tool
def list_subnets(vpc_id: str = "", region: str = "") -> str:
    """List subnets across regions, optionally filtered by VPC ID."""
    result = _merge_results("VPC", "ListSubnets", region or None, "subnets")
    empty = validate_empty_result(result, "VPC", "ListSubnets")
    if empty:
        return json.dumps({"ok": True, "service": "VPC", "operation": "ListSubnets", "data": None, "item_count": 0, "message": empty})
    return _dump(result)


VPC_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_vpcs, service="VPC", category=ToolCategory.QUERY,
        keywords=["vpc", "virtual private cloud", "red", "network", "networks"],
        is_read_only=True, cacheable=True, cache_ttl=30,
    ),
    ToolMeta(
        tool=describe_vpc, service="VPC", category=ToolCategory.QUERY,
        keywords=["describe vpc", "vpc detail", "vpc status"],
        is_read_only=True, cacheable=True, cache_ttl=15,
    ),
    ToolMeta(
        tool=create_vpc, service="VPC", category=ToolCategory.DEPLOY,
        keywords=["create vpc", "crear vpc", "deploy vpc", "desplegar vpc"],
        is_read_only=False, cacheable=False,
    ),
    ToolMeta(
        tool=list_subnets, service="VPC", category=ToolCategory.QUERY,
        keywords=["subnet", "subnets", "subred", "subredes"],
        is_read_only=True, cacheable=True, cache_ttl=30,
    ),
]
