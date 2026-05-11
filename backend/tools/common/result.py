from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    data: Any | None = None
    error: str | None = None
    raw: str | None = None
