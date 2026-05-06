import os
import re
import subprocess
from pathlib import Path
from langchain_core.tools import tool

TF_DIR = Path(__file__).parent / "terraform_workspace"
TF_DIR.mkdir(exist_ok=True)

TF_RESOURCES_DIR = Path(__file__).parent / "terraform_resources"

_PROVIDER_PREFIX_MAP = {"hcso_": "huaweicloud_"}

_RESOURCE_ALIASES = {
    "ecs_instance": "compute_instance",
    "ecs_keypair": "compute_keypair",
    "ecs_servergroup": "compute_servergroup",
    "ecs_volume_attach": "compute_volume_attach",
    "ecs_interface_attach": "compute_interface_attach",
    "elb_loadbalancer": "elb_loadbalancer_v3",
    "evs_volume": "evs_volume_v3",
}

def _build_resource_index() -> dict[str, Path]:
    index = {}
    if not TF_RESOURCES_DIR.exists():
        return index
    for md_file in TF_RESOURCES_DIR.glob("*.md"):
        resource_name = md_file.stem
        index[resource_name] = md_file
    return index

_RESOURCE_INDEX = _build_resource_index()

def _translate_provider_prefix(content: str) -> str:
    for src, dst in _PROVIDER_PREFIX_MAP.items():
        content = content.replace(src, dst)
    return content

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    fm = {}
    body = content
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if m:
        for line in m.group(1).strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip().strip('"').strip("'")
        body = m.group(2)
    return fm, body

@tool
def deploy_with_terraform(tf_code: str) -> str:
    """Implementa o despliega infraestructura en Huawei Cloud usando Terraform.
    El LLM debe proporcionar el codigo HCL (Terraform) completo y valido para los
    recursos (ECS, VPC, SG, EIP, ELB, RDS) SIN la configuracion del provider, ya 
    que el provedor y credenciales se inyectan automaticamente.
    
    Args:
        tf_code: Código fuente HCL (Terraform) con los recursos a desplegar.
    """
    # 1. Preparar el proveedor
    region = os.getenv("HUAWEI_REGION", "ap-southeast-3")
    ak = os.getenv("HUAWEI_AK", "")
    sk = os.getenv("HUAWEI_SK", "")
    
    provider_config = f"""
terraform {{
  required_providers {{
    huaweicloud = {{
      source  = "huaweicloud/huaweicloud"
      version = "~> 1.60.0"
    }}
  }}
}}

provider "huaweicloud" {{
  region     = "{region}"
  access_key = "{ak}"
  secret_key = "{sk}"
}}
"""
    
    main_tf_path = TF_DIR / "main.tf"
    with open(main_tf_path, "w", encoding="utf-8") as f:
        f.write(provider_config + "\n" + tf_code)
        
    try:
        # 2. Inicializar
        init_res = subprocess.run(
            ["terraform", "init"], cwd=TF_DIR, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if init_res.returncode != 0:
            return f"Error en terraform init:\n{init_res.stderr}"
            
        # 3. Aplicar
        apply_res = subprocess.run(
            ["terraform", "apply", "-auto-approve"], cwd=TF_DIR, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if apply_res.returncode != 0:
            return f"Error en terraform apply:\n{apply_res.stderr}"
            
        return "Despliegue exitoso."
    except Exception as e:
        return f"Error al ejecutar terraform: {str(e)}"

@tool
def destroy_infrastructure_with_terraform() -> str:
    """Destruye toda la infraestructura previamente creada con Terraform en el workspace actual.
    Muy rápido y eficiente para limpiar todo el entorno o cuando el usuario pide eliminar todo lo creado.
    No requiere conectarse a KooCLI.
    """
    try:
        if not (TF_DIR / "main.tf").exists():
            return "No hay infraestructura gestionada por Terraform para destruir actualmente."
            
        destroy_res = subprocess.run(
            ["terraform", "destroy", "-auto-approve"], cwd=TF_DIR, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if destroy_res.returncode != 0:
            return f"Error en terraform destroy:\n{destroy_res.stderr}"
            
        return "Toda la infraestructura de Terraform fue eliminada correctamente."
    except Exception as e:
        return f"Error al ejecutar terraform destroy: {str(e)}"


@tool
def list_terraform_resources() -> str:
    """Lista todos los recursos de Terraform disponibles en Huawei Cloud con su subcategoria.
    Usa esta herramienta para descubrir que recursos existen antes de buscar documentacion."""
    if not _RESOURCE_INDEX:
        return f"Error: No se encontraron archivos .md en {TF_RESOURCES_DIR}"

    by_subcategory: dict[str, list[str]] = {}
    for resource_name, md_path in sorted(_RESOURCE_INDEX.items()):
        with open(md_path, "r", encoding="utf-8") as f:
            fm, _ = _parse_frontmatter(f.read())
        subcat = fm.get("subcategory", "Other")
        by_subcategory.setdefault(subcat, []).append(resource_name)

    lines = ["Recursos de Terraform disponibles (huaweicloud provider):\n"]
    for subcat in sorted(by_subcategory.keys()):
        resources = by_subcategory[subcat]
        lines.append(f"  [{subcat}] ({len(resources)} recursos)")
        for r in resources:
            lines.append(f"    - huaweicloud_{r}")

    lines.append(f"\nTotal: {len(_RESOURCE_INDEX)} recursos")
    lines.append("Siguiente: resolve_terraform_resource(resource='vpc') para ver documentacion y ejemplos HCL.")
    return "\n".join(lines)


@tool
def resolve_terraform_resource(resource: str, section: str = "all") -> str:
    """Resuelve la documentacion de un recurso de Terraform de Huawei Cloud.
    Retorna ejemplos HCL y argumentos (requeridos/opcionales) para que el agente
    genere codigo Terraform preciso. CRITICO: Usa esta herramienta ANTES de generar
    codigo HCL con deploy_with_terraform para evitar errores de sintaxis o argumentos
    incorrectos.

    Args:
        resource: Nombre del recurso SIN el prefijo del provider.
                  Ej: 'vpc', 'vpc_subnet', 'ecs_instance', 'rds_instance', 'elb_loadbalancer'.
                  Acepta tanto con como sin prefijo (hcso_vpc, huaweicloud_vpc, vpc).
        section: Seccion a retornar: 'examples' (solo ejemplos HCL),
                 'arguments' (solo argumentos), o 'all' (completo, por defecto).
    """
    clean = resource.lower().strip()
    for prefix in ("huaweicloud_", "hcso_"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]

    clean = _RESOURCE_ALIASES.get(clean, clean)

    md_path = _RESOURCE_INDEX.get(clean)
    if not md_path:
        close = [r for r in _RESOURCE_INDEX if clean in r]
        msg = f"Recurso '{resource}' no encontrado."
        if close:
            msg += f" Quiza quisiste decir: {', '.join('huaweicloud_' + c for c in close[:5])}"
        msg += " Usa list_terraform_resources() para ver todos los recursos."
        return msg

    with open(md_path, "r", encoding="utf-8") as f:
        raw = f.read()

    fm, body = _parse_frontmatter(raw)
    body = _translate_provider_prefix(body)

    if section == "examples":
        parts = []
        in_example = False
        current: list[str] = []
        for line in body.splitlines():
            if line.strip().startswith("```hcl"):
                in_example = True
                current = [line]
                continue
            if in_example:
                current.append(line)
                if line.strip() == "```":
                    in_example = False
                    parts.append("\n".join(current))
        if parts:
            return f"[Ejemplos HCL para huaweicloud_{clean}]\n\n" + "\n\n".join(parts)
        return f"No se encontraron ejemplos HCL para huaweicloud_{clean}."

    if section == "arguments":
        arg_match = re.search(r"## Argument Reference\n(.*)", body, re.DOTALL)
        if arg_match:
            arg_text = arg_match.group(1)
            attr_match = re.search(r"\n## Attribute Reference\n", arg_text)
            if attr_match:
                arg_text = arg_text[:attr_match.start()]
            return f"[Argumentos para huaweicloud_{clean}]\n\n{arg_text.strip()}"
        return f"No se encontraron argumentos para huaweicloud_{clean}."

    max_chars = 12000
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n...[Documentacion truncada. Usa section='examples' o section='arguments' para secciones especificas.]"

    return f"[Documentacion de huaweicloud_{clean}]\nSubcategoria: {fm.get('subcategory', 'N/A')}\n\n{body}"


@tool
def resolve_terraform_resources(resources: str) -> str:
    """Resuelve la documentacion de MULTIPLES recursos de Terraform en una sola llamada.
    Retorna ejemplos HCL compactos y argumentos requeridos para cada recurso.
    USA ESTA HERRAMIENTA cuando necesitas desplegar una arquitectura con varios recursos
    (VPC, Subnet, ECS, ELB, etc.) en vez de llamar resolve_terraform_resource multiples veces.
    Esto es mucho mas rapido y eficiente.

    Args:
        resources: Lista de nombres de recursos separados por coma, SIN prefijo del provider.
                   Ej: 'vpc,vpc_subnet,compute_instance,vpc_eip,elb_loadbalancer_v3'
                   Acepta aliases: 'vpc,vpc_subnet,ecs_instance,vpc_eip,elb_loadbalancer'
    """
    names = [r.strip() for r in resources.split(",") if r.strip()]
    if not names:
        return "Error: proporciona al menos un nombre de recurso separado por coma."

    results = []
    not_found = []
    budget_per_resource = 6000

    for raw_name in names:
        clean = raw_name.lower().strip()
        for prefix in ("huaweicloud_", "hcso_"):
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        clean = _RESOURCE_ALIASES.get(clean, clean)

        md_path = _RESOURCE_INDEX.get(clean)
        if not md_path:
            not_found.append(raw_name)
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            raw = f.read()

        fm, body = _parse_frontmatter(raw)
        body = _translate_provider_prefix(body)

        examples = []
        in_example = False
        current: list[str] = []
        for line in body.splitlines():
            if line.strip().startswith("```hcl"):
                in_example = True
                current = [line]
                continue
            if in_example:
                current.append(line)
                if line.strip() == "```":
                    in_example = False
                    examples.append("\n".join(current))

        arg_match = re.search(r"## Argument Reference\n(.*)", body, re.DOTALL)
        arg_text = ""
        if arg_match:
            arg_text = arg_match.group(1)
            attr_match = re.search(r"\n## Attribute Reference\n", arg_text)
            if attr_match:
                arg_text = arg_text[:attr_match.start()]
            import_match = re.search(r"\n## Import\n", arg_text)
            if import_match:
                arg_text = arg_text[:import_match.start()]
            arg_text = arg_text.strip()

        section_parts = [f"### huaweicloud_{clean} [{fm.get('subcategory', 'N/A')}]"]
        if examples:
            section_parts.append(f"\nEjemplo HCL:\n{examples[0]}")
        if arg_text:
            if len(arg_text) > 3000:
                arg_text = arg_text[:3000] + "\n...[argumentos truncados]"
            section_parts.append(f"\nArgumentos:\n{arg_text}")

        combined = "\n".join(section_parts)
        if len(combined) > budget_per_resource:
            combined = combined[:budget_per_resource] + "\n...[truncado]"
        results.append(combined)

    output = "\n\n---\n\n".join(results)
    if not_found:
        output += f"\n\n---\nNo encontrados: {', '.join(not_found)}. Usa list_terraform_resources() para ver todos."

    return output

