import json
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_koocli_json


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True)


@tool
def list_eips(region: str = "") -> str:
    """List public IPs (EIPs) in a region."""
    params = {"cli-region": region} if region else None
    result = run_koocli_json("EIP", "ListPublicips", params)
    payload = {
        "ok": result.ok,
        "service": "EIP",
        "operation": "ListPublicips",
        "data": result.data if result.ok else None,
        "error": result.error,
    }
    return _dump(payload)
