from typing import Any

from langchain_core.tools import tool

from koocli.executor import execute_koocli
from utils.sanitize import sanitize_params, validate_service_name, validate_operation_name
from validators.security import is_destructive_operation
from tools.registry import ToolMeta, ToolCategory
from config.logging import get_logger

logger = get_logger("tools.koocli")

DEPLOY_REDIRECTS = {
    ("ELB", "CreateLoadBalancer"): "setup_elb_for_ecs",
    ("ECS", "NovaCreateServers"): "deploy_ecs_instance",
    ("ECS", "CreateServers"): "deploy_ecs_instance",
    ("ECS", "CreatePostPaidServers"): "deploy_ecs_instance",
    ("ECS", "BatchStartServers"): "manage_ecs",
    ("ECS", "BatchStopServers"): "manage_ecs",
    ("ECS", "BatchRebootServers"): "manage_ecs",
    ("EIP", "CreatePublicip"): "manage_eip",
    ("EIP", "AssociatePublicips"): "manage_eip",
}


@tool
def run_koocli_command(service: str, operation: str, params: dict = None) -> str:
    """Executes a Huawei Cloud KooCLI (hcloud) command.
    For operations that don't have a dedicated tool: first call list_service_operations
    and get_operation_details (or resolve_service_schema) so operation names and params
    come from schema, not from memory.
    For creating ECS/ELB via create APIs, use dedicated deploy tools instead.

    Args:
        service: Huawei Cloud service, e.g. 'ecs', 'vpc', 'iam'.
        operation: Operation to perform, e.g. 'NovaListServers', 'CreateVpc'.
        params: Dictionary with command parameters.
    """
    try:
        service = validate_service_name(service)
        operation = validate_operation_name(operation)
    except ValueError as e:
        return str(e)

    redirect = DEPLOY_REDIRECTS.get((service.upper(), operation))
    if redirect:
        msg = (
            f"STOP: Do not use run_koocli_command for {service}/{operation}. "
            f"Use the dedicated tool `{redirect}` instead."
        )
        logger.warning("Deploy operation redirected: %s", msg)
        return msg

    if params:
        params = sanitize_params(params)

    if is_destructive_operation(operation):
        logger.warning(
            "Destructive operation detected",
            extra={"structured_extra": {"service": service, "operation": operation}},
        )

    result = execute_koocli(service, operation, params)

    logger.info(
        "KooCLI tool executed",
        extra={"structured_extra": {"service": service, "operation": operation, "result_len": len(result)}},
    )

    return result


KOOCLI_TOOLS: list = [
    ToolMeta(
        tool=run_koocli_command, service="KOOCLI", category=ToolCategory.QUERY,
        keywords=["koocli", "hcloud", "run command", "ejecutar comando"],
        is_read_only=True, cacheable=False,
    ),
]
