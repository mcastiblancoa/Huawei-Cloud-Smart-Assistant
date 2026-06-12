import json
from typing import Any

from langchain_core.tools import tool

from config.settings import get_settings
from services.billing import get_monthly_billing_summary
from tools.common.koocli_runner import run_cloud_command
from tools.common.table_formatter import format_billing_table
from tools.registry import ToolMeta, ToolCategory
from cloud.result import CloudResult
from cloud.validation import validate_empty_result


def _dump(result: CloudResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True)


@tool
def get_monthly_costs(bill_cycle: str) -> str:
    """Get monthly billing summary for a bill cycle (YYYY-MM). Returns real billing data from Huawei Cloud."""
    settings = get_settings()
    data = get_monthly_billing_summary(settings, bill_cycle)

    if data.get("error"):
        return json.dumps({
            "ok": False, "service": "BSSINTL", "operation": "ShowCustomerMonthlySum",
            "error": data["error"],
        })

    table_md = format_billing_table(data.get("services", []), [data.get("month", bill_cycle)])

    return json.dumps({
        "ok": True, "service": "BSSINTL", "operation": "ShowCustomerMonthlySum",
        "data": data, "item_count": len(data.get("services", [])),
        "_table": table_md,
    })


@tool
def get_cost_by_service(bill_cycle: str) -> str:
    """Get costs broken down by service for a given month (YYYY-MM). Returns real data only."""
    settings = get_settings()
    data = get_monthly_billing_summary(settings, bill_cycle)

    if data.get("error"):
        return json.dumps({"ok": False, "service": "BSSINTL", "error": data["error"]})

    services = data.get("services", [])
    if not services:
        return json.dumps({
            "ok": True, "service": "BSSINTL", "data": {"month": bill_cycle, "services": [], "total": 0},
            "item_count": 0, "message": f"No se encontraron datos de facturación para {bill_cycle}.",
        })

    table_md = format_billing_table(services, [data.get("month", bill_cycle)])

    return json.dumps({
        "ok": True, "service": "BSSINTL", "data": data, "item_count": len(services),
        "_table": table_md,
    })


BILLING_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=get_monthly_costs, service="BSSINTL", category=ToolCategory.BILLING,
        keywords=["billing", "cost", "costs", "gasto", "factura", "facturacion", "bill", "spend", "monthly"],
        is_read_only=True, cacheable=True, cache_ttl=120,
    ),
    ToolMeta(
        tool=get_cost_by_service, service="BSSINTL", category=ToolCategory.BILLING,
        keywords=["cost by service", "costos por servicio", "gasto por servicio"],
        is_read_only=True, cacheable=True, cache_ttl=120,
    ),
]
