import os
import subprocess
from pathlib import Path
from langchain_core.tools import tool

TF_DIR = Path(__file__).parent / "terraform_workspace"
TF_DIR.mkdir(exist_ok=True)

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
        init_res = subprocess.run(["terraform", "init"], cwd=TF_DIR, capture_output=True, text=True)
        if init_res.returncode != 0:
            return f"Error en terraform init:\n{init_res.stderr}"
            
        # 3. Aplicar
        apply_res = subprocess.run(["terraform", "apply", "-auto-approve"], cwd=TF_DIR, capture_output=True, text=True)
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
            
        destroy_res = subprocess.run(["terraform", "destroy", "-auto-approve"], cwd=TF_DIR, capture_output=True, text=True)
        if destroy_res.returncode != 0:
            return f"Error en terraform destroy:\n{destroy_res.stderr}"
            
        return "Toda la infraestructura de Terraform fue eliminada correctamente."
    except Exception as e:
        return f"Error al ejecutar terraform destroy: {str(e)}"

