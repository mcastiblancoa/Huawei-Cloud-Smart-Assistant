import re
from typing import Any


_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


def _safe(value: Any) -> str:
    if value is None:
        return ""
    s = str(value)
    s = _UUID_RE.sub("", s).strip()
    if s in ("None", "none", "null"):
        return ""
    return s


def format_table(items: list[dict], columns: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    headers = [col[1] for col in columns]
    keys = [col[0] for col in columns]
    rows = []
    for item in items:
        row = []
        for key in keys:
            val = item
            for part in key.split("."):
                if isinstance(val, dict):
                    val = val.get(part, "")
                else:
                    val = ""
                    break
            row.append(_safe(val))
        rows.append(row)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |")
    return "\n".join([header_line, sep_line] + body_lines)


_RESOURCE_TYPE_COLUMNS = {
    "cloudservers": [("name", "Nombre"), ("region_id", "Region")],
    "publicips": [("name", "IP Publica"), ("region_id", "Region")],
    "vpcs": [("name", "Nombre"), ("region_id", "Region")],
    "subnets": [("name", "Nombre"), ("region_id", "Region")],
    "securityGroups": [("name", "Nombre"), ("region_id", "Region")],
    "loadbalancers": [("name", "Nombre"), ("region_id", "Region")],
    "volumes": [("name", "Nombre"), ("region_id", "Region")],
    "bandwidths": [("name", "Nombre"), ("region_id", "Region")],
    "images": [("name", "Nombre"), ("region_id", "Region")],
    "agents": [("name", "Nombre"), ("region_id", "Region")],
    "keys": [("name", "Nombre"), ("region_id", "Region")],
    "routetables": [("name", "Nombre"), ("region_id", "Region")],
    "buckets": [("name", "Nombre"), ("region_id", "Region")],
    "databases": [("name", "Nombre"), ("region_id", "Region")],
}

_RESOURCE_TYPE_LABELS = {
    "cloudservers": "ECS",
    "publicips": "EIP",
    "vpcs": "VPC",
    "subnets": "Subnet",
    "securityGroups": "Security Group",
    "loadbalancers": "ELB",
    "volumes": "EVS Volume",
    "bandwidths": "Bandwidth",
    "images": "Image (IMS)",
    "agents": "Agent (HSS)",
    "keys": "Key (KMS)",
    "routetables": "Route Table",
    "buckets": "OBS Bucket",
    "databases": "RDS",
}


def format_billing_table(services: list[dict], months: list[str]) -> str:
    if not services and not months:
        return ""
    if not months:
        months = ["?"]
    month_labels = [m for m in months]
    if len(month_labels) == 1:
        headers = ["Servicio", f"{month_labels[0]} (USD)"]
    else:
        headers = ["Servicio"] + [f"{m} (USD)" for m in month_labels]
    col_widths = [len(h) for h in headers]
    rows = []
    all_services: dict[str, list[str]] = {}
    for svc in services:
        name = svc.get("name", "?")
        amount = f"{svc.get('amount', 0):.2f}"
        if name not in all_services:
            all_services[name] = ["0.00"] * len(month_labels)
        all_services[name][0] = amount
    for name in sorted(all_services.keys(), key=lambda n: -float(all_services[n][0])):
        row = [name] + all_services[name]
        rows.append(row)
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |")
    return "\n".join([header_line, sep_line] + body_lines)


def format_billing_table_multi(monthly_data: list[dict]) -> str:
    if not monthly_data:
        return ""
    seen_months = set()
    unique_data = []
    for d in monthly_data:
        month = d.get("month", "?")
        if month not in seen_months:
            seen_months.add(month)
            unique_data.append(d)
    monthly_data = unique_data
    months = [d.get("month", "?") for d in monthly_data]
    all_services: dict[str, list[str]] = {}
    service_order: list[str] = []
    for d in monthly_data:
        month = d.get("month", "?")
        services = d.get("services", [])
        for svc in services:
            name = svc.get("name", "?")
            amount = f"{svc.get('amount', 0):.2f}"
            if name not in all_services:
                all_services[name] = {}
                service_order.append(name)
            all_services[name][month] = amount
    totals: dict[str, str] = {}
    for i, month in enumerate(months):
        total = monthly_data[i].get("total", 0)
        totals[month] = f"{total:.2f}"
    headers = ["Servicio"] + [f"{m} (USD)" for m in months]
    rows = []
    for name in service_order:
        row = [name]
        for month in months:
            row.append(all_services.get(name, {}).get(month, "0.00"))
        rows.append(row)
    total_row = ["TOTAL"]
    for month in months:
        total_row.append(totals.get(month, "0.00"))
    rows.append(total_row)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |")
    return "\n".join([header_line, sep_line] + body_lines)


def format_resources_grouped(items: list[dict]) -> str:
    if not items:
        return ""
    by_type: dict[str, list[dict]] = {}
    for item in items:
        t = item.get("type", "unknown")
        by_type.setdefault(t, []).append(item)
    sorted_types = sorted(by_type.items(), key=lambda x: -len(x[1]))
    parts = []
    for t, group in sorted_types:
        label = _RESOURCE_TYPE_LABELS.get(t, t)
        columns = _RESOURCE_TYPE_COLUMNS.get(t, [("name", "Nombre"), ("region_id", "Region")])
        table = format_table(group, columns)
        if table:
            parts.append(f"**{label}** ({len(group)})\n\n{table}")
    return "\n\n".join(parts)


ECS_COLUMNS = [
    ("name", "Nombre"),
    ("_region", "Region"),
    ("_status_display", "Estado"),
    ("_flavor_display", "Flavor"),
]

EIP_COLUMNS = [
    ("public_ip_address", "IP Publica"),
    ("_region", "Region"),
    ("status", "Estado"),
    ("type", "Tipo"),
    ("bandwidth.name", "Bandwidth"),
]

VPC_COLUMNS = [
    ("name", "Nombre"),
    ("_region", "Region"),
    ("status", "Estado"),
    ("cidr", "CIDR"),
]

SUBNET_COLUMNS = [
    ("name", "Nombre"),
    ("_region", "Region"),
    ("cidr", "CIDR"),
    ("vpc_id", "VPC"),
]

ELB_COLUMNS = [
    ("name", "Nombre"),
    ("_region", "Region"),
    ("provisioning_status", "Estado"),
    ("vip_address", "VIP"),
]

SG_COLUMNS = [
    ("name", "Nombre"),
    ("_region", "Region"),
]

RDS_COLUMNS = [
    ("name", "Nombre"),
    ("_region", "Region"),
    ("status", "Estado"),
    ("datastore.type", "Engine"),
    ("datastore.version", "Version"),
]


def _parse_billing_table(table_md: str) -> tuple[list[str], dict[str, list[str]]]:
    lines = table_md.strip().split("\n")
    headers = []
    services = {}
    for line in lines:
        if not line.strip() or not line.includes("|") if hasattr(line, 'includes') else "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not headers:
            headers = cells
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        name = cells[0]
        values = cells[1:]
        services[name] = values
    return headers, services


def merge_billing_tables(tables: list[str]) -> str | None:
    if len(tables) <= 1:
        return tables[0] if tables else None
    all_months = []
    all_services: dict[str, dict[str, str]] = {}
    service_order: list[str] = []
    for table_md in tables:
        lines = table_md.strip().split("\n")
        headers = []
        for line in lines:
            if "|" not in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not headers:
                headers = cells
                continue
            if all(set(c) <= set("-: ") for c in cells):
                continue
            name = cells[0]
            values = cells[1:]
            for i, h in enumerate(headers[1:]):
                month = h.replace(" (USD)", "").strip()
                if month not in all_months:
                    all_months.append(month)
                if name not in all_services:
                    all_services[name] = {}
                    if name != "TOTAL":
                        service_order.append(name)
                all_services[name][month] = values[i] if i < len(values) else "0.00"
    if not all_months:
        return None
    headers = ["Servicio"] + [f"{m} (USD)" for m in all_months]
    rows = []
    for name in service_order:
        row = [name] + [all_services.get(name, {}).get(m, "0.00") for m in all_months]
        rows.append(row)
    if "TOTAL" in all_services:
        total_row = ["TOTAL"] + [all_services["TOTAL"].get(m, "0.00") for m in all_months]
        rows.append(total_row)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |")
    return "\n".join([header_line, sep_line] + body_lines)
