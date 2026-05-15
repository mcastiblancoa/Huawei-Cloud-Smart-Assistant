import json
from typing import Any

from langchain_core.tools import tool

from schemas.registry import ServiceRegistry
from utils.sanitize import sanitize_params, validate_service_name, validate_operation_name
from tools.registry import ToolMeta, ToolCategory


@tool
def list_available_services() -> str:
    """Lists all Huawei Cloud KooCLI services (90+) with operation counts.
    Call this when the user asks what is possible on Huawei Cloud, or when you need
    to pick a service name before listing operations (next: list_service_operations)."""
    registry = ServiceRegistry.get()
    return registry.get_available_services_text()


@tool
def list_service_operations(service: str) -> str:
    """Lists every hcloud operation for a service (e.g. ECS, VPC, ELB).
    REQUIRED before run_koocli_command when you are not 100% sure of the exact
    operation name or when no dedicated tool covers the user's request.

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
    """Returns full KooCLI schema for one operation: description, required/optional params.
    Use after list_service_operations (or resolve_service_schema) and BEFORE
    run_koocli_command so you never guess parameter names.

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
    """Fast path: load service schema from disk; optional operation_hint narrows operations.
    Prefer list_service_operations + get_operation_details when you need the full list;
    use this when you already know the service and roughly which API you need.

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


DISCOVERY_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_available_services, service="DISCOVERY", category=ToolCategory.DISCOVERY,
        keywords=["list services", "available services", "servicios disponibles"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
    ToolMeta(
        tool=list_service_operations, service="DISCOVERY", category=ToolCategory.DISCOVERY,
        keywords=["list operations", "service operations", "operaciones"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
    ToolMeta(
        tool=get_operation_details, service="DISCOVERY", category=ToolCategory.DISCOVERY,
        keywords=["operation details", "schema", "parametros", "parameters"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
    ToolMeta(
        tool=resolve_service_schema, service="DISCOVERY", category=ToolCategory.DISCOVERY,
        keywords=["resolve schema", "resolve service"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
]
