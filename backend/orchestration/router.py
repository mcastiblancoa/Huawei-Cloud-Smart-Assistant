import re
from dataclasses import dataclass
from typing import Any


@dataclass
class RouteDecision:
    tool: str
    params: dict[str, Any]
    response_type: str
    is_fast_path: bool = True


_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}")


def _find_uuid(text: str) -> str | None:
    match = _UUID_RE.search(text)
    return match.group(0) if match else None


def _parse_bill_cycle(message: str) -> str | None:
    for token in message.replace("/", "-").split():
        if len(token) == 7 and token[4] == "-" and token[:4].isdigit() and token[5:7].isdigit():
            return token
    import re as _re
    months_map = {
        "enero": "01", "january": "01", "febrero": "02", "february": "02",
        "marzo": "03", "march": "03", "abril": "04", "april": "04",
        "mayo": "05", "may": "05", "junio": "06", "june": "06",
        "julio": "07", "july": "07", "agosto": "08", "august": "08",
        "septiembre": "09", "september": "09", "octubre": "10", "october": "10",
        "noviembre": "11", "november": "11", "diciembre": "12", "december": "12",
    }
    lower = message.lower()
    year_match = _re.search(r'\b(20[2-9]\d)\b', message)
    year = year_match.group(1) if year_match else None
    for month_name, month_num in months_map.items():
        if month_name in lower:
            if year:
                return f"{year}-{month_num}"
            from datetime import datetime
            return f"{datetime.now().year}-{month_num}"
    return None


def route_intent(message: str) -> RouteDecision | None:
    text = message.lower().strip()
    target_id = _find_uuid(message)

    _COMPOSITE_KEYWORDS = [
        "encender", "enciende", "encend", "apagar", "apaga", "detener", "detene",
        "asignar", "asigna", "colocar", "coloca", "anclar", "dar", "dame",
        "crear y", "desplegar y", "start and", "create and", "deploy and",
        "si no", "if not", "si no tiene", "y dame", "and give",
        "reboot", "reiniciar", "restart",
    ]
    if any(kw in text for kw in _COMPOSITE_KEYWORDS):
        return None

    if any(kw in text for kw in ["billing", "cost", "costs", "gasto", "gast", "factura", "facturacion", "bill", "spend", "cuanto"]):
        bill_cycle = _parse_bill_cycle(message)
        if not bill_cycle:
            from datetime import datetime
            now = datetime.now()
            bill_cycle = f"{now.year}-{now.month:02d}"
        if "servicio" in text or "by service" in text or "por servicio" in text:
            return RouteDecision(tool="get_cost_by_service", params={"bill_cycle": bill_cycle}, response_type="billing")
        return RouteDecision(tool="get_monthly_costs", params={"bill_cycle": bill_cycle}, response_type="billing")

    if any(kw in text for kw in ["recurso", "recursos", "resources", "todos los servicios", "all resources", "inventario", "inventory", "what resource", "what service", "mis servicios", "servicios tengo", "tengo desplegado", "lista detallada", "dame una lista", "qué servicios", "que servicios", "servicios desplegado"]):
        return RouteDecision(tool="list_resources", params={}, response_type="resources")

    if any(kw in text for kw in ["ecs", "server", "servers", "instancia", "instancias", "vm", "virtual machine"]):
        if any(kw in text for kw in ["start", "iniciar", "encender", "arrancar"]):
            if target_id:
                return RouteDecision(tool="start_ecs", params={"server_id": target_id}, response_type="ecs_action")
            return None
        if any(kw in text for kw in ["stop", "detener", "parar", "apagar"]):
            if target_id:
                return RouteDecision(tool="stop_ecs", params={"server_id": target_id}, response_type="ecs_action")
            return None
        if any(kw in text for kw in ["reboot", "reiniciar", "restart"]):
            if target_id:
                return RouteDecision(tool="reboot_ecs", params={"server_id": target_id}, response_type="ecs_action")
            return None
        if target_id:
            return RouteDecision(tool="describe_ecs", params={"server_id": target_id}, response_type="ecs")
        return RouteDecision(tool="list_ecs", params={}, response_type="ecs")

    if any(kw in text for kw in ["vpc", "virtual private cloud", "red", "network"]) and not any(kw in text for kw in ["subnet", "subred"]):
        if target_id:
            return RouteDecision(tool="describe_vpc", params={"vpc_id": target_id}, response_type="vpc")
        return RouteDecision(tool="list_vpcs", params={}, response_type="vpc")

    if any(kw in text for kw in ["subnet", "subred", "subredes", "subnets"]):
        return RouteDecision(tool="list_subnets", params={}, response_type="subnet")

    if any(kw in text for kw in ["security group", "security groups", "grupo de seguridad", "grupos de seguridad", "sg"]):
        if target_id:
            return RouteDecision(tool="describe_security_group", params={"security_group_id": target_id}, response_type="security")
        return RouteDecision(tool="list_security_groups", params={}, response_type="security")

    if any(kw in text for kw in ["elb", "load balancer", "balanceador", "loadbalancer"]):
        if target_id:
            return RouteDecision(tool="describe_elb", params={"loadbalancer_id": target_id}, response_type="elb")
        return RouteDecision(tool="list_elb", params={}, response_type="elb")

    if any(kw in text for kw in ["eip", "public ip", "ip publica", "ip pública", "elastic ip"]):
        return RouteDecision(tool="list_eips", params={}, response_type="eip")

    return None
