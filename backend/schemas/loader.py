import json
from pathlib import Path
from typing import Optional

from config.settings import get_settings

_settings = get_settings()
_DATA_DIR = Path(_settings.schema_data_dir)

_AUTO_INJECTED_PARAMS = frozenset({
    "cli-region", "cli-access-key", "cli-secret-key", "project_id", "domain_id",
})


def _resolve_data_dir() -> Path:
    override = _settings.schema_data_dir
    if override:
        p = Path(override)
        if p.exists():
            return p
    return _DATA_DIR


class SchemaLoader:
    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or _resolve_data_dir()
        self._index_cache: Optional[list] = None
        self._schema_cache: dict[str, dict] = {}

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    def load_index(self) -> list:
        if self._index_cache is not None:
            return self._index_cache
        index_path = self._data_dir / "_index.json"
        if not index_path.exists():
            return []
        with open(index_path, "r", encoding="utf-8-sig") as f:
            self._index_cache = json.load(f)
        return self._index_cache

    def load_service(self, service: str) -> Optional[dict]:
        if service in self._schema_cache:
            return self._schema_cache[service]
        safe_name = service.replace("-", "_").replace(" ", "_")
        for candidate in [f"{service}.json", f"{safe_name}.json"]:
            path = self._data_dir / candidate
            if path.exists():
                with open(path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    self._schema_cache[service] = data
                    return data
        return None

    def find_operation(self, schema: dict, operation: str) -> Optional[dict]:
        for op in schema.get("operations", []):
            if op["operation"] == operation:
                return op
        return None

    def fuzzy_match_operations(self, schema: dict, query: str, limit: int = 5) -> list[str]:
        q = query.lower()
        matches = []
        for op in schema.get("operations", []):
            if q in op["operation"].lower():
                matches.append(op["operation"])
        return matches[:limit]

    def list_services(self) -> list[dict]:
        return self.load_index()

    def get_service_names(self) -> list[str]:
        return [e["service"] for e in self.load_index()]

    def get_operations_by_method(self, schema: dict) -> dict[str, list[str]]:
        by_method: dict[str, list[str]] = {}
        for op in schema.get("operations", []):
            method = op.get("method", "UNKNOWN")
            by_method.setdefault(method, []).append(op["operation"])
        return by_method

    def get_operation_params(self, op_schema: dict) -> tuple[list[dict], list[dict], list[dict]]:
        required = []
        optional = []
        auto = []
        seen_required: dict[str, dict] = {}
        seen_optional: dict[str, dict] = {}

        for p in op_schema.get("parameters", []):
            name = p["name"]
            if name in _AUTO_INJECTED_PARAMS:
                auto.append(p)
            elif p.get("required", False):
                if name not in seen_required:
                    seen_required[name] = {**p, "count": 1}
                else:
                    seen_required[name]["count"] += 1
            else:
                if name not in seen_optional:
                    seen_optional[name] = {**p, "count": 1}
                else:
                    seen_optional[name]["count"] += 1

        required = list(seen_required.values())
        optional = list(seen_optional.values())
        return required, optional, auto

    def clear_cache(self) -> None:
        self._index_cache = None
        self._schema_cache.clear()


_auto_injected_params = _AUTO_INJECTED_PARAMS
