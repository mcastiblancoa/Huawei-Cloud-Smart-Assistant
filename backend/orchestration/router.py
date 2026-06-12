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


def _normalize_for_routing(text: str) -> str:
    """Fix common typos so intent routing still matches (user message to LLM is unchanged)."""
    t = text
    # "puedes deplegar" (missing 's') should still skip ECS list fast-path
    t = t.replace("deplegar", "desplegar")
    return t


_INFORMATIONAL_RE = re.compile(
    r"\b(qué es|que es|what is|what are|qué son|que son|explain|explica|explicame|define|defin|"
    r"how does|cómo funciona|como funciona|tell me about|hablame de|háblame de|"
    r"para qué sirve|para que sirve|what does|para qué se usa|para que se usa|"
    r"diferencia entre|difference between|vs\b|versus)\b",
    re.I,
)


def _looks_like_informational(text: str) -> bool:
    return bool(_INFORMATIONAL_RE.search(text))


_ECS_STANDALONE_RE = re.compile(r"(?<![\w-])ecs(?![\w-])", re.I)


def _ecs_topic_hit(text: str) -> bool:
    """True if the user is talking about ECS as a topic, not hostnames like 'ecs-test'."""
    if _ECS_STANDALONE_RE.search(text):
        return True
    return any(
        kw in text
        for kw in (
            "server",
            "servers",
            "instancia",
            "instancias",
            "vm",
            "virtual machine",
        )
    )


def _looks_like_ecs_deploy_params(text: str) -> bool:
    """Follow-up messages with flavor / image are part of ECS deploy, not inventory listing."""
    if re.search(r"\bs\d+\.[\w.-]+\b", text, re.I):
        return True
    if "flavor" in text or "flavour" in text:
        return True
    if "ubuntu" in text and any(x in text for x in ("22.04", "20.04", "24.04", "imagen", "image")):
        return True
    return False


def _looks_like_deploy_request(text: str) -> bool:
    """Deploy/create requests must use the full agent (deploy tools, discovery, etc.),
    not keyword fast-path list tools."""
    if any(
        k in text
        for k in (
            "desplegar",
            "deploy",
            "provisionar",
            "provisiona",
            "infraestructura",
            "alta disponibilidad",
            "high availability",
        )
    ):
        return True
    if "lanzar" in text and any(k in text for k in ("ecs", "instancia", "elb", "vm", "servidor")):
        return True
    if "crear" in text and any(
        k in text
        for k in (
            "ecs",
            "instancia",
            "elb",
            "vpc",
            "servidor",
            "balanceador",
            "load balancer",
            "loadbalancer",
            "rds",
            "database",
            "base de datos",
            "mysql",
            "postgres",
        )
    ):
        return True
    return False


_BILLING_INTENT_RE = re.compile(
    r"\b(billing|invoices?|factura|facturaci[oó]n|spend|spending|"
    r"gastos?|cu[aá]nto|costos?|coste|\bcost\b|presupuesto|budget)\b",
    re.I,
)


def _looks_like_billing_intent(text: str) -> bool:
    """Word-boundary billing intent (avoid 'gast' inside 'desplegaste', 'cost' inside unrelated words)."""
    return bool(_BILLING_INTENT_RE.search(text))


def _looks_like_delete_request(text: str) -> bool:
    """Tear-down / cleanup must use full agent, never billing fast-path."""
    if not re.search(
        r"\b(borr(ar|a|o)?|elimina(r|d|s)?|delete|remove|destroy|terminate|termina(r)?|"
        r"limpia(r)?|tear\s*down|liber(ar|a)?)\b",
        text,
        re.I,
    ):
        return False
    return bool(
        re.search(
            r"\b(ecs|elb|eips?|vpcs?|sgs?|security\s*group|servidor|servidores|instancia|instancias|recurso|recursos|"
            r"balanceador|balanceadores|load\s*balancer|infraestructura|todo|bucket|obs|rds|database|base\s*de\s*datos)\b",
            text,
            re.I,
        )
    )


def route_intent(message: str) -> RouteDecision | None:
    text = _normalize_for_routing(message.lower().strip())
    target_id = _find_uuid(message)

    _COMPOSITE_KEYWORDS = [
        "encender", "enciende", "encend", "apagar", "apaga", "detener", "detene",
        "asignar", "asigna", "colocar", "coloca", "anclar", "dar", "dame",
        "crear y", "desplegar y", "start and", "create and", "deploy and",
        "si no", "if not", "si no tiene", "y dame", "and give",
        "reboot", "reiniciar", "restart",
        "borrar", "borra", "eliminar", "elimina", "delete", "remove",
        "liberar", "libera",
    ]
    if any(kw in text for kw in _COMPOSITE_KEYWORDS):
        return None

    if _looks_like_deploy_request(text):
        return None

    if _looks_like_ecs_deploy_params(text):
        return None

    if _looks_like_delete_request(text):
        return None

    if _looks_like_informational(text):
        return None

    if _looks_like_billing_intent(text):
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

    if _ecs_topic_hit(text):
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

    if any(kw in text for kw in ["rds", "base de datos", "base datos", "database", "mysql", "postgres", "sqlserver", "mariadb", "db instance"]):
        if any(kw in text for kw in ["version", "versions", "motor", "engines", "datastore"]):
            return RouteDecision(tool="list_rds_datastores", params={}, response_type="rds")
        if any(kw in text for kw in ["flavor", "flavors", "specs", "especificaciones", "tamaños", "sizes"]):
            return RouteDecision(tool="list_rds_flavors", params={}, response_type="rds")
        return RouteDecision(tool="list_rds", params={}, response_type="rds")

    return None
