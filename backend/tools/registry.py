from langchain_core.tools import BaseTool

from tools.discovery import (
    list_available_services,
    list_service_operations,
    get_operation_details,
    resolve_service_schema,
)
from tools.koocli import run_koocli_command
from tools.deploy import deploy_elb_loadbalancer, deploy_ecs_instance, deploy_vpc, deploy_full_stack


DEFAULT_TOOLS: list[BaseTool] = [
    resolve_service_schema,
    list_available_services,
    list_service_operations,
    get_operation_details,
    run_koocli_command,
    deploy_elb_loadbalancer,
    deploy_ecs_instance,
    deploy_vpc,
    deploy_full_stack,
]


def get_all_tools() -> list[BaseTool]:
    return list(DEFAULT_TOOLS)


def get_tools_by_name(names: list[str]) -> list[BaseTool]:
    available = {t.name: t for t in DEFAULT_TOOLS}
    return [available[n] for n in names if n in available]
