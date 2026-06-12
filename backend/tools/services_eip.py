import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_cloud_command
from tools.common.table_formatter import format_table, EIP_COLUMNS
from tools.registry import ToolMeta, ToolCategory
from cloud.result import CloudResult
from cloud.validation import validate_empty_result
from config.settings import get_settings

_PRIMARY_REGIONS = ["la-north-2", "ap-southeast-1", "ap-southeast-3"]


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
def list_eips(region: str = "") -> str:
    """List all public IPs (EIPs) across regions. Returns real data from Huawei Cloud."""
    result = _merge_results("EIP", "ListPublicips", region or None, "publicips")
    empty = validate_empty_result(result, "EIP", "ListPublicips")
    if empty:
        return json.dumps({"ok": True, "service": "EIP", "operation": "ListPublicips", "data": None, "item_count": 0, "message": empty})
    items = result.data.get("publicips", []) if isinstance(result.data, dict) else []
    table_md = format_table(items, EIP_COLUMNS)
    d = result.to_dict()
    if table_md:
        d["_table"] = table_md
    return json.dumps(d, ensure_ascii=True)


@tool
def create_eip(region: str = "ap-southeast-3", bandwidth_size: int = 5, charge_mode: str = "traffic") -> str:
    """Create a new Elastic IP (EIP) on Huawei Cloud."""
    params = {
        "cli-region": region,
        "publicip": {"type": "5_bgp"},
        "bandwidth": {"name": f"eip-bw-{int(__import__('time').time()) % 100000}", "size": bandwidth_size, "charge_mode": charge_mode, "share_type": "PER"},
    }
    result = run_cloud_command("EIP", "CreatePublicip", params, use_cache=False)
    return _dump(result)


@tool
def associate_eip(eip_id: str, resource_id: str, resource_type: str = "ECS", region: str = "ap-southeast-3") -> str:
    """Associate an EIP to an ECS or ELB."""
    if resource_type.upper() == "ELB":
        params = {
            "cli-region": region,
            "publicip_id": eip_id,
            "publicip": {"associate_instance_id": resource_id, "associate_instance_type": "ELB"},
        }
        result = run_cloud_command("EIP", "AssociatePublicips", params, use_cache=False)
    else:
        from koocli.executor import execute_koocli
        from cloud.validation import extract_id
        detail = execute_koocli("ECS", "ShowServer", {"cli-region": region, "server_id": resource_id})
        port_id = extract_id(detail, [r'"port_id":\s*"([^"]+)"'])
        if not port_id:
            import re
            all_ports = re.findall(r'"port_id":\s*"([^"]+)"', detail)
            port_id = all_ports[0] if all_ports else ""
        if not port_id:
            return json.dumps({"ok": False, "error": f"Could not find port_id for server {resource_id}"})
        params = {"cli-region": region, "publicip_id": eip_id, "publicip": {"port_id": port_id}}
        result = run_cloud_command("EIP", "UpdatePublicip", params, use_cache=False)
    return _dump(result)


@tool
def release_eip(eip_id: str, region: str = "ap-southeast-3") -> str:
    """Release (delete) an Elastic IP by ID."""
    params = {"cli-region": region, "publicip_id": eip_id}
    result = run_cloud_command("EIP", "DeletePublicip", params, use_cache=False)
    return _dump(result)


EIP_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_eips, service="EIP", category=ToolCategory.QUERY,
        keywords=["eip", "public ip", "ip publica", "ip pública", "elastic ip"],
        is_read_only=True, cacheable=True, cache_ttl=30,
    ),
    ToolMeta(
        tool=create_eip, service="EIP", category=ToolCategory.DEPLOY,
        keywords=["create eip", "crear eip", "allocate eip"],
        is_read_only=False, cacheable=False,
    ),
    ToolMeta(
        tool=associate_eip, service="EIP", category=ToolCategory.MANAGE,
        keywords=["associate eip", "bind eip", "asociar eip"],
        is_read_only=False, cacheable=False,
    ),
    ToolMeta(
        tool=release_eip, service="EIP", category=ToolCategory.DELETE,
        keywords=["release eip", "delete eip", "eliminar eip"],
        is_read_only=False, is_destructive=True, cacheable=False,
    ),
]
