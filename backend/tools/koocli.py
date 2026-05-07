from typing import Any

from langchain_core.tools import tool

from koocli.executor import execute_koocli
from utils.sanitize import sanitize_params, validate_service_name, validate_operation_name
from validators.security import is_destructive_operation, get_confirmation_message
from config.logging import get_logger

logger = get_logger("tools.koocli")

DEPLOY_REDIRECTS = {
    ("ELB", "BatchCreateLoadBalancers"): "deploy_elb_loadbalancer",
    ("ELB", "CreateLoadBalancer"): "deploy_elb_loadbalancer",
    ("ECS", "NovaCreateServers"): "deploy_ecs_instance",
    ("ECS", "CreateServers"): "deploy_ecs_instance",
    ("VPC", "CreateVpc"): "deploy_vpc",
}


@tool
def run_koocli_command(service: str, operation: str, params: dict = None) -> str:
    """Executes a Huawei Cloud KooCLI (hcloud) command.

    IMPORTANT: Before using this tool, ALWAYS verify required parameters
    with get_operation_details(). If any required parameter is missing,
    ask the user first; do NOT invent values.

    IMPORTANT: For creating resources (ELB, ECS, VPC), use the dedicated
    deploy tools instead: deploy_elb_loadbalancer, deploy_ecs_instance, deploy_vpc.
    Do NOT use this tool for resource creation.

    Nested body parameters are passed as dicts and automatically converted
    to KooCLI dot notation.
    Example: params={'vpc': {'name': 'my-vpc', 'cidr': '10.0.0.0/16'}}
    Becomes: --vpc.name my-vpc --vpc.cidr 10.0.0.0/16

    Args:
        service: Huawei Cloud service, e.g. 'ecs', 'vpc', 'iam'.
        operation: Operation to perform, e.g. 'ListCloudServers', 'CreateVpc'.
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
            f"Use the dedicated tool `{redirect}` instead. "
            f"It handles parameter construction correctly and prevents errors."
        )
        logger.warning("Deploy operation redirected: %s", msg)
        return msg

    if params:
        params = sanitize_params(params)

    if is_destructive_operation(operation):
        logger.warning(
            "Destructive operation detected",
            extra={"structured_extra": {
                "service": service,
                "operation": operation,
            }},
        )

    result = execute_koocli(service, operation, params)

    logger.info(
        "KooCLI tool executed",
        extra={"structured_extra": {
            "service": service,
            "operation": operation,
            "result_len": len(result),
        }},
    )

    return result
