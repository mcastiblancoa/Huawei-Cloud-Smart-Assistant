import os
import subprocess
import json
from pathlib import Path
from langchain_core.tools import tool

# ─── Configuración de rutas ───────────────────────────────────────────────────
SCHEMA_DIR = Path(os.getenv(
    "HUAWEI_SCHEMA_DIR",
    str(Path(__file__).parent / "services_schema")
))

AUTO_INJECTED_PARAMS = {"cli-region", "cli-access-key", "cli-secret-key", "project_id"}

# ─── Diagnóstico al importar ──────────────────────────────────────────────────
_index_path = SCHEMA_DIR / "_index.json"
if _index_path.exists():
    with open(_index_path, "r", encoding="utf-8-sig") as f:
        _idx = json.load(f)
    print(f"✅ Schema cargado: {SCHEMA_DIR} ({len(_idx)} servicios)")
else:
    print(f"⚠️  ADVERTENCIA: No se encontró {SCHEMA_DIR}/_index.json")


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _load_index() -> list:
    index_path = SCHEMA_DIR / "_index.json"
    if not index_path.exists():
        return []
    with open(index_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _load_service_schema(service: str) -> dict | None:
    safe_name = service.replace("-", "_").replace(" ", "_")
    for candidate in [f"{service}.json", f"{safe_name}.json"]:
        path = SCHEMA_DIR / candidate
        if path.exists():
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
    return None


def _find_operation(schema: dict, operation: str) -> dict | None:
    for op in schema.get("operations", []):
        if op["operation"] == operation:
            return op
    return None


def _fuzzy_match_operations(schema: dict, query: str, limit: int = 5) -> list[str]:
    matches = []
    q = query.lower()
    for op in schema.get("operations", []):
        if q in op["operation"].lower():
            matches.append(op["operation"])
    return matches[:limit]


def _flatten_params(params: dict, prefix: str = "") -> list[tuple[str, str]]:
    """Convierte dicts anidados a dot notation de KooCLI.
    
    Ejemplo:
        {'vpc': {'name': 'pruebita', 'cidr': '10.0.0.0/16'}}
        → [('vpc.name', 'pruebita'), ('vpc.cidr', '10.0.0.0/16')]
        
        {'server': {'name': 'test', 'flavorRef': 'c2.large', 'nics': [{'subnet_id': 'id1'}]}}
        → [('server.name', 'test'), ('server.flavorRef', 'c2.large'), ('server.nics.1.subnet_id', 'id1')]
    """
    result = []
    for key, value in params.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            # Dict → recursión (dot notation)
            result.extend(_flatten_params(value, full_key))
        elif isinstance(value, list):
            # Lista → aplanar con índices basados en 1 (formato hcloud)
            if all(not isinstance(v, (dict, list)) for v in value):
                # Array de primitivos: usa índices 1, 2, 3...
                for i, v in enumerate(value, start=1):
                    result.append((f"{full_key}.{i}", str(v)))
            else:
                # Array de objetos: recursión para cada elemento
                for i, v in enumerate(value, start=1):
                    if isinstance(v, dict):
                        # Aplanar cada dict del array con índice basado en 1
                        result.extend(_flatten_params(v, f"{full_key}.{i}"))
                    elif isinstance(v, list):
                        result.append((f"{full_key}.{i}", json.dumps(v, separators=(',', ':'))))
                    else:
                        result.append((f"{full_key}.{i}", str(v)))
        elif isinstance(value, str) and value.strip().startswith(('{', '[')):
            # String que parece JSON → intentar parsear y aplanar
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    result.extend(_flatten_params(parsed, full_key))
                elif isinstance(parsed, list):
                    if all(not isinstance(v, (dict, list)) for v in parsed):
                        for i, v in enumerate(parsed, start=1):
                            result.append((f"{full_key}.{i}", str(v)))
                    else:
                        for i, v in enumerate(parsed, start=1):
                            if isinstance(v, dict):
                                result.extend(_flatten_params(v, f"{full_key}.{i}"))
                            else:
                                result.append((f"{full_key}.{i}", str(v)))
                else:
                    result.append((full_key, value))
            except json.JSONDecodeError:
                result.append((full_key, value))
        else:
            result.append((full_key, str(value)))
    return result


# ════════════════════════════════════════════════════════════════════════════
# TOOL 0: Resolucion directa de schema (bypass LLM reasoning)
# ════════════════════════════════════════════════════════════════════════════

@tool
def resolve_service_schema(service: str, operation_hint: str = "") -> str:
    """Resolucion DIRECTA de schema: carga inmediatamente el JSON de un servicio
    y retorna operaciones disponibles + detalles de la operacion si se proporciona
    operation_hint. Usa esta herramienta cuando ya sabes el nombre del servicio
    (ej. 'ECS', 'VPC', 'RDS', 'ELB') para evitar pasos innecesarios de razonamiento.

    Args:
        service: Nombre exacto del servicio, ej. 'ECS', 'VPC', 'RDS', 'ELB', 'IAM'
        operation_hint: Nombre parcial o completo de la operacion buscada (opcional).
                        Si se proporciona, retorna los detalles de la operacion encontrada.
    """
    schema = _load_service_schema(service)
    if not schema:
        # Intentar fuzzy match contra el indice
        index = _load_index()
        available = [e["service"] for e in index]
        close = [s for s in available if service.lower() in s.lower()]
        msg = f"Servicio '{service}' no encontrado."
        if close:
            msg += f" Quiza quisiste decir: {', '.join(close[:5])}"
        msg += " Usa list_available_services() para ver todos los servicios."
        return msg

    # Si hay operation_hint, buscar la operacion directamente
    if operation_hint:
        # Busqueda exacta primero
        op_schema = _find_operation(schema, operation_hint)
        if op_schema:
            # Retornar detalles completos de la operacion
            lines = [f"[DIRECT LOOKUP] {service} -> {operation_hint}"]
            lines.append(f"Metodo: {op_schema.get('method', 'N/A')}")
            lines.append(f"Comando: hcloud {service} {operation_hint}")
            if op_schema.get("description"):
                lines.append(f"Descripcion: {op_schema['description']}")

            required = [p for p in op_schema.get("parameters", [])
                       if p.get("required") and p["name"] not in AUTO_INJECTED_PARAMS]
            optional = [p for p in op_schema.get("parameters", [])
                       if not p.get("required") and p["name"] not in AUTO_INJECTED_PARAMS]

            if required:
                lines.append(f"\nREQUERIDOS ({len(required)}):")
                for p in required:
                    lines.append(f"  --{p['name']} tipo={p['type']}")
            if optional:
                lines.append(f"\nOPCIONALES ({len(optional)}):")
                for p in optional:
                    lines.append(f"  --{p['name']} tipo={p['type']}")

            lines.append(f"\nEjecutar: run_koocli_command(service='{service}', operation='{operation_hint}', params={{...}})")
            return "\n".join(lines)

        # Fuzzy match si no se encuentra exacto
        suggestions = _fuzzy_match_operations(schema, operation_hint)
        if suggestions:
            return (f"[DIRECT LOOKUP] {service}: operacion '{operation_hint}' no exacta.\n"
                    f"Candidatos: {', '.join(suggestions)}\n"
                    f"Usa get_operation_details('{service}', '<operacion_exacta>') para detalles completos.")

    # Sin operation_hint: retornar resumen del servicio
    lines = [f"[DIRECT LOOKUP] {service} ({schema['total_operations']} operaciones):"]
    by_method: dict[str, list[str]] = {}
    for op in schema["operations"]:
        method = op.get("method", "?")
        by_method.setdefault(method, []).append(op["operation"])

    for method in ["POST", "GET", "PUT", "DELETE"]:
        if method in by_method:
            lines.append(f"  [{method}] ({len(by_method[method])}): {', '.join(by_method[method][:8])}")
            if len(by_method[method]) > 8:
                lines.append(f"         ...y {len(by_method[method]) - 8} mas")

    lines.append(f"\nSiguiente: resolve_service_schema(service='{service}', operation_hint='<operacion>')")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# TOOL 1: Listar servicios disponibles
# ════════════════════════════════════════════════════════════════════════════

@tool
def list_available_services() -> str:
    """Lista todos los servicios disponibles de Huawei Cloud KooCLI con su cantidad de operaciones.
    Usa esta herramienta para descubrir qué servicios existen antes de buscar operaciones."""
    index = _load_index()
    if not index:
        return (f"Error: No se encontró el índice en {SCHEMA_DIR}/_index.json. "
                "Ejecuta primero generate_all_services_json.ps1")

    lines = ["Servicios disponibles de Huawei Cloud KooCLI:\n"]
    for entry in index:
        lines.append(f"  * {entry['service']:30s} ({entry['total_operations']} ops)")

    lines.append(f"\nTotal: {len(index)} servicios")
    lines.append("Siguiente paso: usa list_service_operations('<servicio>') para ver las operaciones.")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# TOOL 2: Listar operaciones de un servicio
# ════════════════════════════════════════════════════════════════════════════

@tool
def list_service_operations(service: str) -> str:
    """Lista todas las operaciones disponibles para un servicio de Huawei Cloud,
    agrupadas por metodo HTTP (POST, GET, PUT, DELETE).
    
    Args:
        service: Nombre del servicio, ej. 'ECS', 'VPC', 'RDS', 'IAM'
    """
    schema = _load_service_schema(service)
    if not schema:
        return (f"Error: No se encontro schema para '{service}'. "
                "Usa list_available_services() para ver los servicios disponibles.")

    lines = [f"Operaciones de {service} ({schema['total_operations']} total):\n"]

    by_method: dict[str, list[str]] = {}
    for op in schema["operations"]:
        method = op.get("method", "UNKNOWN")
        by_method.setdefault(method, []).append(op["operation"])

    for method in ["POST", "GET", "PUT", "DELETE", "PATCH", "UNKNOWN"]:
        if method not in by_method:
            continue
        lines.append(f"\n  [{method}] ({len(by_method[method])} operaciones)")
        for op_name in by_method[method]:
            lines.append(f"      {op_name}")

    lines.append(f"\nSiguiente paso: usa get_operation_details('{service}', '<operacion>') "
                 "para ver los parametros requeridos y opcionales.")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# TOOL 3: Obtener detalles de una operacion
# ════════════════════════════════════════════════════════════════════════════

@tool
def get_operation_details(service: str, operation: str) -> str:
    """Obtiene el schema completo de una operacion: metodo HTTP, descripcion,
    y parametros requeridos/opcionales con sus tipos.
    
    CRITICO: Usa esta herramienta ANTES de ejecutar cualquier comando para saber
    exactamente que parametros necesitas. Si falta algun parametro REQUERIDO,
    preguntale al usuario ANTES de ejecutar el comando.
    
    Args:
        service: Nombre del servicio, ej. 'ECS'
        operation: Nombre de la operacion, ej. 'NovaCreateServers'
    """
    schema = _load_service_schema(service)
    if not schema:
        return f"Error: No se encontro schema para '{service}'."

    op_schema = _find_operation(schema, operation)

    if not op_schema:
        suggestions = _fuzzy_match_operations(schema, operation)
        msg = f"Operacion '{operation}' no encontrada en '{service}'."
        if suggestions:
            msg += f"\nQuiza quisiste decir: {', '.join(suggestions)}"
        msg += f"\nUsa list_service_operations('{service}') para ver todas las operaciones."
        return msg

    lines = []
    lines.append("=" * 65)
    lines.append(f"Servicio:     {service}")
    lines.append(f"Operacion:    {operation}")
    lines.append(f"Metodo HTTP:  {op_schema.get('method', 'N/A')}")
    lines.append(f"Comando:      hcloud {service} {operation}")
    if op_schema.get("description"):
        lines.append(f"Descripcion:  {op_schema['description']}")
    lines.append("=" * 65)

    # Clasificar parametros (deduplicando nombres repetidos = body param)
    required_params = []
    optional_params = []
    auto_params = []
    seen_required = {}
    seen_optional = {}

    for p in op_schema.get("parameters", []):
        name = p["name"]
        if name in AUTO_INJECTED_PARAMS:
            auto_params.append(p)
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

    required_params = list(seen_required.values())
    optional_params = list(seen_optional.values())

    # Parametros REQUERIDOS
    if required_params:
        lines.append(f"\nREQUERIDOS ({len(required_params)}):")
        for p in required_params:
            name = p["name"]
            loc = f" [{p['location']}]" if p.get("location") else ""
            if p["count"] > 1:
                lines.append(f"    --{name:30s} (body object){loc}")
                lines.append(f"        ^ Pasar como dict anidado en params.")
                lines.append(f"          Ej: params={{'{name}': {{'field1': 'val1', 'field2': 'val2'}}}}")
            else:
                lines.append(f"    --{name:30s} tipo={p['type']}{loc}")
    else:
        lines.append(f"\nNo hay parametros requeridos (ademas de los auto-inyectados).")

    # Parametros OPCIONALES
    if optional_params:
        lines.append(f"\nOPCIONALES ({len(optional_params)}):")
        for p in optional_params:
            name = p["name"]
            loc = f" [{p['location']}]" if p.get("location") else ""
            if p["count"] > 1:
                lines.append(f"    --{name:30s} (body object){loc}")
                lines.append(f"        ^ Pasar como dict anidado en params.")
                lines.append(f"          Ej: params={{'{name}': {{'field1': 'val1'}}}}")
            else:
                lines.append(f"    --{name:30s} tipo={p['type']}{loc}")

    # Auto-inyectados
    if auto_params:
        lines.append(f"\nAUTO-INYECTADOS (NO los proporciones):")
        for p in auto_params:
            lines.append(f"    --{p['name']}")

    # Resumen
    lines.append(f"\n" + "-" * 65)
    if required_params:
        req_names = [f"--{p['name']}" for p in required_params]
        lines.append(f"RESUMEN: Antes de ejecutar, asegurate de tener: {', '.join(req_names)}")
        lines.append(f"   Si el usuario no proporciono alguno, PREGUNTALE antes de ejecutar.")
    else:
        lines.append(f"Esta operacion no requiere parametros adicionales. Puedes ejecutarla directamente.")

    lines.append(f"\nEjemplo: run_koocli_command(service='{service}', operation='{operation}', params={{...}})")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# TOOL 4: Ejecutar comando KooCLI
# ════════════════════════════════════════════════════════════════════════════

@tool
def run_koocli_command(service: str, operation: str, params: dict = None) -> str:
    """Ejecuta un comando de KooCLI (hcloud) de Huawei Cloud.
    
    IMPORTANTE: Antes de usar esta herramienta, SIEMPRE verifica los parametros
    requeridos con get_operation_details(). Si falta algun parametro requerido,
    preguntale al usuario primero; NO inventes valores.
    
    Los parametros body anidados se pasan como dicts y se convierten
    automaticamente a dot notation de KooCLI.
    Ejemplo: params={'vpc': {'name': 'mi-vpc', 'cidr': '10.0.0.0/16'}}
    Se convierte en: --vpc.name mi-vpc --vpc.cidr 10.0.0.0/16
    
    Args:
        service: El servicio de Huawei Cloud, ej. 'ecs', 'vpc', 'iam'.
        operation: La operacion a realizar, ej. 'ListCloudServers', 'CreateVpc'.
        params: Diccionario con los parametros del comando.
                Para body params anidados, usa dicts:
                {'vpc': {'name': 'mi-vpc', 'cidr': '10.0.0.0/16'}}
    """
    ak = os.getenv("HUAWEI_AK")
    sk = os.getenv("HUAWEI_SK")
    project_id = os.getenv("HUAWEI_PROJECT_ID")
    region = os.getenv("HUAWEI_REGION")

    if not ak or not sk or not region:
        return "Error: Faltan credenciales (HUAWEI_AK, HUAWEI_SK, HUAWEI_REGION) en el .env"

    # Override región para servicios que requieren región específica
    REGION_OVERRIDES = {
        "BSSINTL": "ap-southeast-1",
    }
    if service.upper() in REGION_OVERRIDES:
        region = REGION_OVERRIDES[service.upper()]

    import shutil
    hcloud_path = shutil.which("hcloud")
    if not hcloud_path:
        # Try common relative locations from the workspace root
        _workspace = Path(__file__).resolve().parent.parent
        _candidates = [
            _workspace / "bin" / "hcloud.exe",
            _workspace / "hcloud.exe",
            Path.home() / "Downloads" / "huaweicloud-cli-windows-amd64" / "hcloud.exe",
        ]
        for candidate in _candidates:
            if candidate.exists():
                hcloud_path = str(candidate)
                break
    if not hcloud_path:
        return "Error: 'hcloud' no esta instalado. Instala KooCLI y asegurate de que este en el PATH."

    cmd = [f'"{hcloud_path}"', service, operation]

    if params:
        # Aplanar dicts anidados a dot notation de KooCLI
        flat_params = _flatten_params(params)
        for key, value in flat_params:
            if key in ("cli-region", "region"):
                region = value
                continue
            if key in AUTO_INJECTED_PARAMS:
                continue
            # Escapar comillas dobles dentro del valor para shell=True
            escaped_value = str(value).replace('"', '\\"')
            cmd.append(f'--{key}="{escaped_value}"')

    # Inyectar autenticacion
    cmd.extend([
        f"--cli-access-key={ak}",
        f"--cli-secret-key={sk}",
        f"--cli-region={region}",
    ])

    # Mapeo de Project IDs por region
    PROJECT_IDS = {
        "af-north-1": "ffd9e2abbbac4f888abd9f08b18dbc3d",
        "ap-southeast-1": "1724bd3fa7f745f79110f3ce49128ecb",
        "ap-southeast-3": "c03f2d01969044fc85baef46ba86a6ec",
        "cn-north-4": "a24fcb85b2204db7b2a90e48ebda08f5",
        "cn-south-1": "8358450edaa3433294d4f21fb22e5d3f",
        "la-north-2": "5785afdda6384c71ba92e8dd741b6ff8",
        "la-south-2": "ddee7698ac56487a9b6248f3567af49a",
        "me-east-1": "019dacb4116c733bbc10896f621443fe",
        "na-mexico-1": "4fde7221d82b4f7ca6b02ed0ca52d8b9",
        "sa-brazil-1": "b2ff2698ac56487a9b6248f3567af49a",
    }

    actual_project_id = PROJECT_IDS.get(region, project_id)
    if actual_project_id and params and "project_id" not in params:
        cmd.append(f"--project_id={actual_project_id}")

    try:
        cmd_str = " ".join(cmd)
        result = subprocess.run(
            cmd_str,
            capture_output=True,
            text=True,
            check=False,
            shell=True
        )

        output = result.stdout if result.returncode == 0 else result.stderr

        # Limitar salida para no exceder contexto del LLM
        max_length = 20000
        if len(output) > max_length:
            output = output[:max_length] + (
                f"\n\n...[ADVERTENCIA: Salida truncada a {max_length} chars. "
                "Sugiere al usuario usar filtros o paginacion.]"
            )

        if result.returncode == 0:
            return f"Exito:\n{output}"
        else:
            return f"Error (codigo {result.returncode}):\n{output}"

    except FileNotFoundError:
        return "Error: 'hcloud' no esta instalado o no se encuentra en el PATH."
    except Exception as e:
        return f"Error inesperado: {str(e)}"