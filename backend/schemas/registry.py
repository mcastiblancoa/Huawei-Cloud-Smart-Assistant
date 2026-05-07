from typing import Optional

from schemas.loader import SchemaLoader


class ServiceRegistry:
    _instance: Optional["ServiceRegistry"] = None

    def __init__(self, loader: Optional[SchemaLoader] = None):
        self._loader = loader or SchemaLoader()

    @classmethod
    def get(cls) -> "ServiceRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    @property
    def loader(self) -> SchemaLoader:
        return self._loader

    def discover_services(self) -> list[dict]:
        return self._loader.list_services()

    def discover_operations(self, service: str) -> Optional[dict]:
        return self._loader.load_service(service)

    def discover_operation_details(self, service: str, operation: str) -> Optional[dict]:
        schema = self._loader.load_service(service)
        if not schema:
            return None
        return self._loader.find_operation(schema, operation)

    def get_available_services_text(self) -> str:
        index = self._loader.list_services()
        if not index:
            return "No services found. Schema index is empty."
        lines = ["Available Huawei Cloud KooCLI services:\n"]
        for entry in index:
            lines.append(f"  * {entry['service']:30s} ({entry['total_operations']} ops)")
        lines.append(f"\nTotal: {len(index)} services")
        return "\n".join(lines)

    def get_service_operations_text(self, service: str) -> str:
        schema = self._loader.load_service(service)
        if not schema:
            available = self._loader.get_service_names()
            close = [s for s in available if service.lower() in s.lower()]
            msg = f"Service '{service}' not found."
            if close:
                msg += f" Did you mean: {', '.join(close[:5])}?"
            return msg

        lines = [f"Operations for {service} ({schema['total_operations']} total):\n"]
        by_method = self._loader.get_operations_by_method(schema)
        for method in ["POST", "GET", "PUT", "DELETE", "PATCH", "UNKNOWN"]:
            if method not in by_method:
                continue
            ops = by_method[method]
            lines.append(f"\n  [{method}] ({len(ops)} operations)")
            for op_name in ops:
                lines.append(f"      {op_name}")
        return "\n".join(lines)

    def get_operation_details_text(self, service: str, operation: str) -> str:
        schema = self._loader.load_service(service)
        if not schema:
            return f"Service '{service}' not found."

        op_schema = self._loader.find_operation(schema, operation)
        if not op_schema:
            suggestions = self._loader.fuzzy_match_operations(schema, operation)
            msg = f"Operation '{operation}' not found in '{service}'."
            if suggestions:
                msg += f"\nDid you mean: {', '.join(suggestions)}?"
            return msg

        required, optional, auto = self._loader.get_operation_params(op_schema)

        lines = [
            "=" * 65,
            f"Service:     {service}",
            f"Operation:   {operation}",
            f"HTTP Method: {op_schema.get('method', 'N/A')}",
            f"Command:     hcloud {service} {operation}",
        ]
        if op_schema.get("description"):
            lines.append(f"Description:  {op_schema['description']}")
        lines.append("=" * 65)

        if required:
            lines.append(f"\nREQUIRED ({len(required)}):")
            for p in required:
                name = p["name"]
                loc = f" [{p['location']}]" if p.get("location") else ""
                if p["count"] > 1:
                    lines.append(f"    --{name:30s} (body object){loc}")
                    lines.append(f"        Pass as nested dict in params.")
                else:
                    lines.append(f"    --{name:30s} type={p['type']}{loc}")
        else:
            lines.append("\nNo required parameters (besides auto-injected).")

        if optional:
            lines.append(f"\nOPTIONAL ({len(optional)}):")
            for p in optional:
                name = p["name"]
                loc = f" [{p['location']}]" if p.get("location") else ""
                if p["count"] > 1:
                    lines.append(f"    --{name:30s} (body object){loc}")
                else:
                    lines.append(f"    --{name:30s} type={p['type']}{loc}")

        if auto:
            lines.append(f"\nAUTO-INJECTED (do not provide):")
            for p in auto:
                lines.append(f"    --{p['name']}")

        return "\n".join(lines)

    def resolve_schema(self, service: str, operation_hint: str = "") -> str:
        schema = self._loader.load_service(service)
        if not schema:
            available = self._loader.get_service_names()
            close = [s for s in available if service.lower() in s.lower()]
            msg = f"Service '{service}' not found."
            if close:
                msg += f" Did you mean: {', '.join(close[:5])}?"
            msg += " Use list_available_services() to see all services."
            return msg

        if operation_hint:
            op_schema = self._loader.find_operation(schema, operation_hint)
            if op_schema:
                return self.get_operation_details_text(service, operation_hint)
            suggestions = self._loader.fuzzy_match_operations(schema, operation_hint)
            if suggestions:
                return (
                    f"Operation '{operation_hint}' not exact in {service}.\n"
                    f"Candidates: {', '.join(suggestions)}\n"
                    f"Use get_operation_details('{service}', '<exact_operation>') for full details."
                )

        lines = [f"{service} ({schema['total_operations']} operations):"]
        by_method = self._loader.get_operations_by_method(schema)
        for method in ["POST", "GET", "PUT", "DELETE"]:
            if method in by_method:
                ops = by_method[method]
                lines.append(f"  [{method}] ({len(ops)}): {', '.join(ops[:8])}")
                if len(ops) > 8:
                    lines.append(f"         ...and {len(ops) - 8} more")
        return "\n".join(lines)
