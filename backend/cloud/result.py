import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CloudResult:
    ok: bool
    service: str = ""
    operation: str = ""
    data: Any = None
    err: str | None = None
    raw: str | None = None
    elapsed_ms: int = 0
    from_cache: bool = False
    validated: bool = False
    item_count: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def error(self) -> str | None:
        return self.err

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "service": self.service,
            "operation": self.operation,
            "data": self.data if self.ok else None,
            "error": self.err,
            "item_count": self.item_count,
            "elapsed_ms": self.elapsed_ms,
            "from_cache": self.from_cache,
            "validated": self.validated,
        }

    @classmethod
    def success(cls, service: str, operation: str, data: Any, raw: str = "", elapsed_ms: int = 0, item_count: int = 0) -> "CloudResult":
        return cls(ok=True, service=service, operation=operation, data=data, raw=raw, elapsed_ms=elapsed_ms, item_count=item_count)

    @classmethod
    def from_error(cls, service: str, operation: str, error: str, elapsed_ms: int = 0) -> "CloudResult":
        return cls(ok=False, service=service, operation=operation, err=error, elapsed_ms=elapsed_ms)

    @classmethod
    def empty(cls, service: str, operation: str, elapsed_ms: int = 0) -> "CloudResult":
        return cls(ok=True, service=service, operation=operation, data=None, elapsed_ms=elapsed_ms, item_count=0, validated=True)
