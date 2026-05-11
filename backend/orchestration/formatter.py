import json
from typing import Any

from cloud.result import CloudResult


def _count_items(data: Any) -> int | None:
    if isinstance(data, dict):
        for key in ["resources", "servers", "vpcs", "subnets", "security_groups", "publicips", "loadbalancers", "bill_sums"]:
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
            if isinstance(value, int):
                return value
    return None


def _build_resource_context(data: Any, response_type: str) -> str:
    if not data or not isinstance(data, dict):
        return ""

    lines = []

    if response_type == "billing":
        month = data.get("month", "")
        total = data.get("total", 0)
        currency = data.get("currency", "USD")
        services = data.get("services", [])
        lines.append(f"Mes: {month}")
        lines.append(f"Total: {total} {currency}")
        if services:
            lines.append("Servicios:")
            for s in services[:15]:
                lines.append(f"  - {s['name']}: {s['amount']} {currency}")
        return "\n".join(lines)

    collection_keys = {
        "ecs": "servers",
        "vpc": "vpcs",
        "subnet": "subnets",
        "security": "security_groups",
        "elb": "loadbalancers",
        "eip": "publicips",
        "resources": "resources",
    }

    key = collection_keys.get(response_type, "")
    items = data.get(key, []) if key else []

    if not items:
        return "Total: 0"

    lines.append(f"Total: {len(items)}")

    if response_type == "resources":
        by_type: dict[str, list] = {}
        for item in items:
            t = item.get("type", "unknown")
            by_type.setdefault(t, []).append(item)
        lines.append("Por tipo:")
        for t, group in sorted(by_type.items(), key=lambda x: -len(x[1])):
            names = [i.get("name", i.get("id", "?"))[:30] for i in group[:5]]
            region = group[0].get("region_id", "")
            lines.append(f"  {t} ({len(group)}): {', '.join(names)} [{region}]")
    else:
        for item in items[:20]:
            name = item.get("name", item.get("id", "?"))
            status = item.get("status", "")
            region = item.get("_region", item.get("region_id", ""))
            info = f"  - {name}"
            if status:
                info += f" ({status})"
            if region:
                info += f" [{region}]"
            flavor = item.get("flavor", {})
            if isinstance(flavor, dict) and flavor.get("name"):
                info += f" flavor={flavor['name']}"
            ip = item.get("public_ip_address", "")
            if ip:
                info += f" ip={ip}"
            lines.append(info)

    return "\n".join(lines)


def _format_billing_natural(data: Any, language: str) -> str:
    if not data or not isinstance(data, dict):
        return ""

    month = data.get("month", "")
    total = data.get("total", 0)
    currency = data.get("currency", "USD")
    services = data.get("services", [])

    h = lambda v: f"<span style='color: #e60012;'><strong>{v}</strong></span>"

    if language == "es":
        month_names = {"01": "enero", "02": "febrero", "03": "marzo", "04": "abril", "05": "mayo", "06": "junio", "07": "julio", "08": "agosto", "09": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre"}
        m_parts = month.split("-")
        month_str = f"{month_names.get(m_parts[1], m_parts[1])} {m_parts[0]}" if len(m_parts) == 2 else month

        text = f"Tu gasto en {month_str} fue de {h(f'{total} {currency}')}."
        if services:
            top = services[0]
            top_amt = f"{top['amount']} {currency}"
            text += f" El mayor gasto fue en {h(top['name'])} con {h(top_amt)}."
            if len(services) > 1:
                others = ", ".join(f"{s['name']} ({s['amount']} {currency})" for s in services[1:4])
                text += f" Otros: {others}."
        return text
    else:
        text = f"Your spending in {month} was {h(f'{total} {currency}')}."
        if services:
            top = services[0]
            top_amt = f"{top['amount']} {currency}"
            text += f" Top spender: {h(top['name'])} at {h(top_amt)}."
        return text


def _format_resources_natural(data: Any, response_type: str, language: str) -> str:
    if not data or not isinstance(data, dict):
        return ""

    h = lambda v: f"<span style='color: #e60012;'><strong>{v}</strong></span>"

    collection_keys = {
        "ecs": "servers", "vpc": "vpcs", "subnet": "subnets",
        "security": "security_groups", "elb": "loadbalancers",
        "eip": "publicips", "resources": "resources",
    }

    key = collection_keys.get(response_type, "")
    items = data.get(key, []) if key else []

    if not items:
        return "No se encontraron recursos." if language == "es" else "No resources found."

    type_labels = {
        "ecs": ("instancias ECS", "ECS instances"),
        "vpc": ("VPCs", "VPCs"),
        "subnet": ("subnets", "subnets"),
        "security": ("security groups", "security groups"),
        "elb": ("load balancers", "load balancers"),
        "eip": ("EIPs", "EIPs"),
        "resources": ("recursos", "resources"),
    }
    label_pair = type_labels.get(response_type, ("recursos", "resources"))
    label = label_pair[0] if language == "es" else label_pair[1]

    if response_type == "resources":
        by_type: dict[str, list] = {}
        for item in items:
            t = item.get("type", "unknown")
            by_type.setdefault(t, []).append(item)

        if language == "es":
            text = f"Tienes {h(str(len(items)))} recursos desplegados en Huawei Cloud.\n\n"
        else:
            text = f"You have {h(str(len(items)))} resources deployed on Huawei Cloud.\n\n"

        type_name_map = {
            "cloudservers": "ECS", "vpcs": "VPC", "subnets": "Subnet",
            "securityGroups": "Security Group", "publicips": "EIP",
            "loadbalancers": "ELB", "volumes": "EVS", "bandwidths": "Bandwidth",
            "routetables": "Route Table", "endpoints": "VPC Endpoint",
            "privatezones": "DNS Private Zone", "agents": "Agent",
            "buckets": "OBS Bucket", "databases": "RDS Database",
        }

        for t, group in sorted(by_type.items(), key=lambda x: -len(x[1])):
            nice_name = type_name_map.get(t, t)
            names = [i.get("name", i.get("id", "?")[:20]) for i in group[:6]]
            region = group[0].get("region_id", "")
            names_str = ", ".join(names)
            if len(group) > 6:
                names_str += f" (+{len(group)-6} más)"
            text += f"{h(nice_name)} ({len(group)}): {names_str} [{region}]\n"

        return text.strip()

    if language == "es":
        text = f"Tienes {h(str(len(items)))} {label}:\n\n"
    else:
        text = f"You have {h(str(len(items)))} {label}:\n\n"

    for item in items[:10]:
        name = item.get("name", item.get("id", "?")[:20])
        status = item.get("status", "")
        region = item.get("_region", item.get("region_id", ""))
        line = f"- {h(name)}"
        if status:
            line += f" ({status})"
        if region:
            line += f" [{region}]"
        text += line + "\n"

    if len(items) > 10:
        text += f"\n...y {len(items) - 10} más."

    return text.strip()


def format_response(response_type: str, payload: dict[str, Any], language: str) -> str:
    if not payload.get("ok"):
        error = payload.get("error", "")
        if language == "es":
            return f"No se pudieron obtener datos reales. {error}" if error else "No se pudieron obtener datos reales."
        return f"Could not retrieve real data. {error}" if error else "Could not retrieve real data."

    msg = payload.get("message")
    if msg and payload.get("item_count", 0) == 0:
        return msg

    data = payload.get("data")

    if response_type == "billing" and data:
        return _format_billing_natural(data, language)

    if data and isinstance(data, dict):
        natural = _format_resources_natural(data, response_type, language)
        if natural:
            return natural

    total = _count_items(data) or 0
    labels = {
        "resources": ("Recursos encontrados", "Resources found"),
        "ecs": ("Instancias ECS encontradas", "ECS instances found"),
        "vpc": ("VPCs encontradas", "VPCs found"),
        "subnet": ("Subnets encontradas", "Subnets found"),
        "security": ("Security groups encontrados", "Security groups found"),
        "elb": ("Load balancers encontrados", "Load balancers found"),
        "eip": ("EIPs encontradas", "EIPs found"),
    }
    label_pair = labels.get(response_type, ("Resultados", "Results found"))
    label = label_pair[0] if language == "es" else label_pair[1]

    if total == 0:
        no_data = "No se encontraron recursos." if language == "es" else "No resources found."
        return f"{label}: <span style='color: #e60012;'><strong>0</strong></span>. {no_data}"

    return f"{label}: <span style='color: #e60012;'><strong>{total}</strong></span>."


def format_cloud_result(result: CloudResult, language: str = "es") -> str:
    if not result.ok:
        if language == "es":
            return f"Error consultando {result.service}: {result.error}"
        return f"Error querying {result.service}: {result.error}"
    if result.item_count == 0:
        if language == "es":
            return f"No se encontraron recursos de {result.service}."
        return f"No {result.service} resources found."
    return result.to_json()
