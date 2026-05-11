import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_koocli_json


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True)


@tool
def list_vpcs(region: str = "") -> str:
    """List VPCs in a region."""
    params = {"cli-region": region} if region else None
    result = run_koocli_json("VPC", "ListVpcs", params)
    payload = {
        "ok": result.ok,
        "service": "VPC",
        "operation": "ListVpcs",
        "data": result.data if result.ok else None,
        "error": result.error,
    }
    return _dump(payload)


@tool
def describe_vpc(vpc_id: str, region: str = "") -> str:
    """Describe a VPC by ID."""
    params = {"vpc_id": vpc_id}
    if region:
        params["cli-region"] = region
    result = run_koocli_json("VPC", "ShowVpc", params)
    payload = {
        "ok": result.ok,
        "service": "VPC",
        "operation": "ShowVpc",
        "data": result.data if result.ok else None,
        "error": result.error,
    }
    return _dump(payload)
