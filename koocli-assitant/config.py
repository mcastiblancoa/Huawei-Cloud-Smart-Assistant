import os
from pathlib import Path
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver

# Load from the consolidated root .env (one level up from this project dir)
_root_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_root_env)

memory = MemorySaver()

# 1. Configuración de herramientas
from huawei_tools import (
    resolve_service_schema,
    list_available_services,
    list_service_operations,
    get_operation_details,
    run_koocli_command,
)

from terraform_tools import (
    deploy_with_terraform,
    destroy_infrastructure_with_terraform,
    resolve_terraform_resource,
    resolve_terraform_resources,
    list_terraform_resources,
)

# Tools del asistente de Huawei Cloud (schema-aware)
# Tavily está comentado: el agente depende de los JSON locales + KooCLI
tools = [
    resolve_service_schema,
    list_available_services,
    list_service_operations,
    get_operation_details,
    run_koocli_command,
    deploy_with_terraform,
    destroy_infrastructure_with_terraform,
    resolve_terraform_resource,
    resolve_terraform_resources,
    list_terraform_resources,
]

# 2. Configuración para Huawei Cloud MaaS
llm = init_chat_model(
    model="glm-5",
    model_provider="openai",
    openai_api_base=os.getenv("OPEN_API_BASE"),
    openai_api_key=os.getenv("MAAS_API_KEY"),
)

llm_with_tools = llm.bind_tools(tools)

graph_config = {
    "configurable": {"thread_id": "1"}
}