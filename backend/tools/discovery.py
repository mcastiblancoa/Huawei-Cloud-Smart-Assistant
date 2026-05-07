from langchain_core.tools import tool

from schemas.registry import ServiceRegistry
from koocli.executor import execute_koocli
from utils.sanitize import sanitize_params, validate_service_name, validate_operation_name
from config.logging import get_logger

logger = get_logger("tools.discovery")


@tool
def list_available_services() -> str:
    """Lists all available Huawei Cloud KooCLI services with their operation counts.
    Use this tool to discover what services exist before searching for operations."""
    registry = ServiceRegistry.get()
    return registry.get_available_services_text()


@tool
def list_service_operations(service: str) -> str:
    """Lists all operations available for a Huawei Cloud service, grouped by HTTP method.

    Args:
        service: Service name, e.g. 'ECS', 'VPC', 'RDS', 'IAM'
    """
    try:
        service = validate_service_name(service)
    except ValueError as e:
        return str(e)
    registry = ServiceRegistry.get()
    return registry.get_service_operations_text(service)


@tool
def get_operation_details(service: str, operation: str) -> str:
    """Gets the full schema of an operation: HTTP method, description,
    and required/optional parameters with their types.

    CRITICAL: Use this tool BEFORE executing any command to know
    exactly what parameters you need. If any REQUIRED parameter is missing,
    ask the user BEFORE executing the command.

    Args:
        service: Service name, e.g. 'ECS'
        operation: Operation name, e.g. 'NovaCreateServers'
    """
    try:
        service = validate_service_name(service)
        operation = validate_operation_name(operation)
    except ValueError as e:
        return str(e)
    registry = ServiceRegistry.get()
    return registry.get_operation_details_text(service, operation)


@tool
def resolve_service_schema(service: str, operation_hint: str = "") -> str:
    """Direct schema resolution: immediately loads a service JSON and returns
    available operations + operation details if operation_hint is provided.

    Args:
        service: Exact service name, e.g. 'ECS', 'VPC', 'RDS', 'ELB', 'IAM'
        operation_hint: Partial or full operation name (optional).
    """
    try:
        service = validate_service_name(service)
    except ValueError as e:
        return str(e)
    registry = ServiceRegistry.get()
    return registry.resolve_schema(service, operation_hint)
