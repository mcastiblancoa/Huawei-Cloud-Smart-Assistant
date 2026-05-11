import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_koocli_json


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True)


@tool
def list_security_groups(region: str = "") -> str:
    """List security groups in a region."""
    params = {"cli-region": region} if region else None
    result = run_koocli_json("VPC", "ListSecurityGroups", params)
    payload = {
        "ok": result.ok,
        "service": "VPC",
        "operation": "ListSecurityGroups",
        "data": result.data if result.ok else None,
        "error": result.error,
    }
    return _dump(payload)


@tool
def describe_security_group(security_group_id: str, region: str = "") -> str:
    """Describe a security group by ID."""
    params = {"security_group_id": security_group_id}
    if region:
        params["cli-region"] = region
    result = run_koocli_json("VPC", "ShowSecurityGroup", params)
    payload = {
        "ok": result.ok,
        "service": "VPC",
        "operation": "ShowSecurityGroup",
        "data": result.data if result.ok else None,
        "error": result.error,
    }
    return _dump(payload)
