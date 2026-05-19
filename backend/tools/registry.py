from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

from langchain_core.tools import BaseTool
from config.logging import get_logger

logger = get_logger("tools.registry")


class ToolCategory(str, Enum):
    QUERY = "query"
    DEPLOY = "deploy"
    MANAGE = "manage"
    DELETE = "delete"
    DISCOVERY = "discovery"
    BILLING = "billing"


@dataclass
class ToolMeta:
    tool: BaseTool
    service: str
    category: ToolCategory
    keywords: list[str] = field(default_factory=list)
    is_read_only: bool = True
    is_destructive: bool = False
    cacheable: bool = True
    cache_ttl: int = 30


class ToolRegistry:
    _instance = None

    def __init__(self):
        self._tools: dict[str, ToolMeta] = {}
        self._service_index: dict[str, list[str]] = {}
        self._keyword_index: dict[str, str] = {}

    @classmethod
    def get(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def _load(self) -> None:
        from tools.services_ecs import ECS_TOOLS
        from tools.services_vpc import VPC_TOOLS
        from tools.services_elb import ELB_TOOLS
        from tools.services_eip import EIP_TOOLS
        from tools.services_sg import SG_TOOLS
        from tools.services_billing import BILLING_TOOLS
        from tools.services_resources import RESOURCES_TOOLS
        from tools.services_discovery import DISCOVERY_TOOLS
        from tools.deploy import DEPLOY_TOOLS
        from tools.koocli import KOOCLI_TOOLS
        from tools.terraform_tools import TERRAFORM_TOOLS

        all_groups = [
            (ECS_TOOLS, "ECS"),
            (VPC_TOOLS, "VPC"),
            (ELB_TOOLS, "ELB"),
            (EIP_TOOLS, "EIP"),
            (SG_TOOLS, "SG"),
            (BILLING_TOOLS, "BSSINTL"),
            (RESOURCES_TOOLS, "RMS"),
            (DISCOVERY_TOOLS, "DISCOVERY"),
            (DEPLOY_TOOLS, "DEPLOY"),
            (KOOCLI_TOOLS, "KOOCLI"),
            (TERRAFORM_TOOLS, "TERRAFORM"),
        ]

        for tools_list, service in all_groups:
            for meta in tools_list:
                self.register(meta)

        logger.info(
            "ToolRegistry loaded",
            extra={"structured_extra": {
                "total_tools": len(self._tools),
                "services": list(self._service_index.keys()),
            }},
        )

    def register(self, meta: ToolMeta) -> None:
        name = meta.tool.name
        self._tools[name] = meta

        svc = meta.service
        if svc not in self._service_index:
            self._service_index[svc] = []
        self._service_index[svc].append(name)

        for kw in meta.keywords:
            self._keyword_index[kw.lower()] = name

    def get_tool(self, name: str) -> BaseTool | None:
        meta = self._tools.get(name)
        return meta.tool if meta else None

    def get_meta(self, name: str) -> ToolMeta | None:
        return self._tools.get(name)

    def get_all_tools(self) -> list[BaseTool]:
        return [m.tool for m in self._tools.values()]

    def get_tools_by_service(self, service: str) -> list[BaseTool]:
        names = self._service_index.get(service.upper(), [])
        return [self._tools[n].tool for n in names if n in self._tools]

    def get_read_only_tools(self) -> list[BaseTool]:
        return [m.tool for m in self._tools.values() if m.is_read_only]

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def resolve_by_keywords(self, text: str) -> str | None:
        lower = text.lower()
        for kw, tool_name in self._keyword_index.items():
            if kw in lower:
                return tool_name
        return None
