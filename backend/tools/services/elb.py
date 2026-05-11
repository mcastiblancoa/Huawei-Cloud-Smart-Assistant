import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_koocli_json


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True)


@tool
def list_elb(region: str = "") -> str:
    """List ELB load balancers in a region."""
    params = {"cli-region": region} if region else None
    result = run_koocli_json("ELB", "ListLoadBalancers", params)
    payload = {
        "ok": result.ok,
        "service": "ELB",
        "operation": "ListLoadBalancers",
        "data": result.data if result.ok else None,
        "error": result.error,
    }
    return _dump(payload)
