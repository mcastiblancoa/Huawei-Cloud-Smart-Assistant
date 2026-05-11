import json
from typing import Any

from langchain_core.tools import tool

from config.settings import get_settings
from services.billing import get_monthly_billing_summary


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True)


@tool
def get_monthly_costs(bill_cycle: str) -> str:
    """Get monthly billing summary for a bill cycle (YYYY-MM)."""
    settings = get_settings()
    data = get_monthly_billing_summary(settings, bill_cycle)
    payload = {
        "ok": data.get("error") is None,
        "service": "BSSINTL",
        "operation": "ShowCustomerMonthlySum",
        "data": data if data.get("error") is None else None,
        "error": data.get("error"),
    }
    return _dump(payload)
