import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from python_terraform import Terraform, IsFlagged
import yaml
from config.settings import get_settings
from config.logging import get_logger

logger = get_logger("tools.terraform_manager")


class TerraformManager:
    """Manager for Terraform operations"""
    
    def __init__(self, working_dir: Optional[str] = None):
        self.settings = get_settings()
        # Get project root directory (two levels up from tools directory)
        project_root = os.path.join(os.path.dirname(__file__), "..", "..")
        self.working_dir = working_dir or os.path.join(project_root, "terraform")
        self.terraform = Terraform(working_dir=self.working_dir)
    
    def _run_terraform_command(self, command: str, temp_dir: str, *args, **kwargs):
        """Run a Terraform command in the specified directory"""
        # Create a new Terraform instance for the temporary directory
        terraform = Terraform(working_dir=temp_dir)
        
        if command == "init":
            return terraform.init(*args, **kwargs)
        elif command == "plan":
            return terraform.plan(*args, **kwargs)
        elif command == "apply":
            return terraform.apply(*args, **kwargs)
        elif command == "output":
            return terraform.output_cmd(*args, **kwargs)
        elif command == "destroy":
            return terraform.destroy(*args, **kwargs)
        else:
            raise ValueError(f"Unknown Terraform command: {command}")
        
    def _get_credentials(self) -> Dict[str, str]:
        """Get Huawei Cloud credentials from settings"""
        return {
            "access_key": self.settings.huawei_ak,
            "secret_key": self.settings.huawei_sk,
            "region_name": self.settings.huawei_region,
        }
    
    def _create_tfvars_file(self, module_dir: str, variables: Dict[str, Any]) -> str:
        """Create a terraform.tfvars file with the given variables"""
        tfvars_path = os.path.join(module_dir, "terraform.tfvars")
        
        # Filter out None values
        filtered_vars = {k: v for k, v in variables.items() if v is not None}
        
        # Write as JSON for consistency
        with open(tfvars_path, 'w') as f:
            json.dump(filtered_vars, f, indent=2)
        
        return tfvars_path
    
    def _create_main_tf(self, module_dir: str, module_source: str, variables: Dict[str, Any]) -> str:
        """Create a main.tf file that uses the module"""
        main_tf_path = os.path.join(module_dir, "main.tf")
        
        # Add credentials to variables
        credentials = self._get_credentials()
        all_variables = {**credentials, **variables}
        
        # Convert path to proper Terraform source format
        # Use relative path from temp_dir to module_source
        module_source_rel = os.path.relpath(module_source, module_dir)
        # Convert to forward slashes for Terraform
        module_source_url = module_source_rel.replace('\\', '/')
        
        main_tf_content = f"""terraform {{
  required_version = ">= 1.9.0"
  required_providers {{
    huaweicloud = {{
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.64.3"
    }}
    random = {{
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }}
  }}
}}

provider "huaweicloud" {{
  region     = "{all_variables.get('region_name', 'ap-southeast-3')}"
  access_key = "{all_variables.get('access_key', '')}"
  secret_key = "{all_variables.get('secret_key', '')}"
}}

module "resource" {{
  source = "{module_source_url}"
  
  # Authentication variables
  region_name = "{all_variables.get('region_name', 'ap-southeast-3')}"
  access_key  = "{all_variables.get('access_key', '')}"
  secret_key  = "{all_variables.get('secret_key', '')}"
  
  # Resource-specific variables
"""
        
        # Add all other variables
        for key, value in all_variables.items():
            if key not in ['region_name', 'access_key', 'secret_key']:
                if isinstance(value, str):
                    main_tf_content += f'  {key} = "{value}"\n'
                elif isinstance(value, bool):
                    main_tf_content += f'  {key} = {str(value).lower()}\n'
                elif isinstance(value, (int, float)):
                    main_tf_content += f'  {key} = {value}\n'
                elif isinstance(value, dict):
                    main_tf_content += f'  {key} = {json.dumps(value)}\n'
                elif isinstance(value, list):
                    main_tf_content += f'  {key} = {json.dumps(value)}\n'
                elif value is None:
                    main_tf_content += f'  {key} = null\n'
        
        main_tf_content += "}\n\n"
        main_tf_content += """output "all_outputs" {
  value = module.resource
}
"""
        
        with open(main_tf_path, 'w') as f:
            f.write(main_tf_content)
        
        return main_tf_path
    
    def deploy_obs_bucket(self, 
                          bucket_name: str,
                          region: Optional[str] = None,
                          storage_class: str = "STANDARD",
                          acl: str = "private",
                          encryption: bool = True,
                          sse_algorithm: str = "kms",
                          encryption_key_id: Optional[str] = None,
                          key_alias: Optional[str] = None,
                          key_usage: str = "ENCRYPT_DECRYPT",
                          force_destroy: bool = True,
                          tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Deploy an OBS bucket using Terraform"""
        
        # Create temporary directory for this deployment
        temp_dir = tempfile.mkdtemp(prefix="terraform_obs_")
        logger.info(f"Creating OBS bucket in temporary directory: {temp_dir}")
        
        try:
            # Prepare variables
            variables = {
                "bucket_name": bucket_name,
                "region_name": region or self.settings.huawei_region,
                "bucket_storage_class": storage_class,
                "bucket_acl": acl,
                "bucket_encryption": encryption,
                "bucket_sse_algorithm": sse_algorithm if encryption else None,
                "bucket_encryption_key_id": encryption_key_id or "",
                "key_alias": key_alias or f"obs-key-{bucket_name}",
                "key_usage": key_usage,
                "bucket_force_destroy": force_destroy,
                "bucket_tags": tags or {},
            }
            
            # Create main.tf
            # Get absolute path to the module
            project_root = os.path.join(os.path.dirname(__file__), "..", "..")
            module_source = os.path.join(project_root, "terraform", "modules", "obs")
            module_source = os.path.abspath(module_source)
            self._create_main_tf(temp_dir, module_source, variables)
            
            # Initialize Terraform
            logger.info("Initializing Terraform...")
            return_code, stdout, stderr = self._run_terraform_command(
                "init", temp_dir,
                capture_output=True,
                no_color=IsFlagged
            )
            
            if return_code != 0:
                raise Exception(f"Terraform init failed: {stderr or stdout}")
            
            # Plan
            logger.info("Creating Terraform plan...")
            return_code, stdout, stderr = self._run_terraform_command(
                "plan", temp_dir,
                capture_output=True,
                no_color=IsFlagged
            )
            
            # Terraform plan returns 0=no changes, 1=error, 2=changes present
            if return_code not in (0, 2):
                raise Exception(f"Terraform plan failed: {stderr or stdout}")
            
            # Apply
            logger.info("Applying Terraform configuration...")
            return_code, stdout, stderr = self._run_terraform_command(
                "apply", temp_dir,
                capture_output=True,
                no_color=IsFlagged,
                skip_plan=True
            )
            
            if return_code != 0:
                raise Exception(f"Terraform apply failed: {stderr or stdout}")
            
            # Get outputs
            return_code, stdout, stderr = self._run_terraform_command(
                "output", temp_dir,
                capture_output=True,
                no_color=IsFlagged,
                json=True
            )
            
            if return_code != 0:
                raise Exception(f"Terraform output failed: {stderr or stdout}")
            
            outputs = json.loads(stdout)
            
            # Destroy temporary directory
            shutil.rmtree(temp_dir)
            
            return {
                "success": True,
                "outputs": outputs,
                "bucket_name": bucket_name,
                "region": region or self.settings.huawei_region,
            }
            
        except Exception as e:
            logger.error(f"Error deploying OBS bucket: {e}")
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "success": False,
                "error": str(e),
                "bucket_name": bucket_name,
            }
    
    def deploy_elb(self,
                  loadbalancer_name: str,
                  vpc_name: str,
                  subnet_name: str,
                  security_group_name: str,
                  instance_name: str,
                  region: Optional[str] = None,
                  availability_zone: Optional[str] = None,
                  instance_flavor_id: Optional[str] = None,
                  instance_flavor_cpu_core_count: int = 2,
                  instance_flavor_memory_size: int = 4,
                  instance_image_id: Optional[str] = None,
                  vpc_cidr: str = "172.16.0.0/16",
                  subnet_cidr: Optional[str] = None,
                  subnet_gateway_ip: Optional[str] = None,
                  is_associate_eip: bool = False,
                  eip_address: Optional[str] = None,
                  bandwidth_name: Optional[str] = None,
                  bandwidth_size: int = 5,
                  listener_name: Optional[str] = None,
                  listener_protocol: str = "HTTP",
                  listener_port: int = 80,
                  pool_name: Optional[str] = None,
                  pool_protocol: str = "HTTP",
                  pool_method: str = "ROUND_ROBIN",
                  member_protocol_port: int = 80,
                  health_check_type: str = "HTTP",
                  health_check_expected_codes: str = "200-202",
                  health_check_url_path: str = "/",
                  health_check_http_method: str = "GET") -> Dict[str, Any]:
        """Deploy an ELB load balancer with ECS instance using Terraform"""
        
        # Create temporary directory for this deployment
        temp_dir = tempfile.mkdtemp(prefix="terraform_elb_")
        logger.info(f"Creating ELB in temporary directory: {temp_dir}")
        
        try:
            # Prepare variables
            variables = {
                "region_name": region or self.settings.huawei_region,
                "availability_zone": availability_zone or "",
                "instance_flavor_id": instance_flavor_id or "",
                "instance_flavor_cpu_core_count": instance_flavor_cpu_core_count,
                "instance_flavor_memory_size": instance_flavor_memory_size,
                "instance_image_id": instance_image_id or "",
                "instance_image_os": "Ubuntu",
                "vpc_name": vpc_name,
                "vpc_cidr": vpc_cidr,
                "subnet_name": subnet_name,
                "subnet_cidr": subnet_cidr or "",
                "subnet_gateway_ip": subnet_gateway_ip or "",
                "loadbalancer_name": loadbalancer_name,
                "is_associate_eip": is_associate_eip,
                "eip_address": eip_address or "",
                "bandwidth_name": bandwidth_name or f"{loadbalancer_name}-bw",
                "bandwidth_size": bandwidth_size,
                "listener_name": listener_name or f"{loadbalancer_name}-listener",
                "listener_protocol": listener_protocol,
                "listener_port": listener_port,
                "pool_name": pool_name or f"{loadbalancer_name}-pool",
                "pool_protocol": pool_protocol,
                "pool_method": pool_method,
                "security_group_name": security_group_name,
                "instance_name": instance_name,
                "member_protocol_port": member_protocol_port,
                "health_check_type": health_check_type,
                "health_check_expected_codes": health_check_expected_codes,
                "health_check_url_path": health_check_url_path,
                "health_check_http_method": health_check_http_method,
                "health_check_name": f"{loadbalancer_name}-health-check",
                "health_check_delay": 10,
                "health_check_timeout": 5,
                "health_check_max_retries": 3,
            }
            
            # Create main.tf
            # Get absolute path to the module
            project_root = os.path.join(os.path.dirname(__file__), "..", "..")
            module_source = os.path.join(project_root, "terraform", "modules", "elb")
            # Convert to absolute path and normalize for Windows
            module_source = os.path.abspath(module_source)
            self._create_main_tf(temp_dir, module_source, variables)
            
            # Initialize Terraform
            logger.info("Initializing Terraform...")
            return_code, stdout, stderr = self._run_terraform_command(
                "init", temp_dir,
                capture_output=True,
                no_color=IsFlagged
            )
            
            if return_code != 0:
                raise Exception(f"Terraform init failed: {stderr or stdout}")
            
            # Plan
            logger.info("Creating Terraform plan...")
            return_code, stdout, stderr = self._run_terraform_command(
                "plan", temp_dir,
                capture_output=True,
                no_color=IsFlagged
            )
            
            # Terraform plan returns 0=no changes, 1=error, 2=changes present
            if return_code not in (0, 2):
                raise Exception(f"Terraform plan failed: {stderr or stdout}")
            
            # Apply
            logger.info("Applying Terraform configuration...")
            return_code, stdout, stderr = self._run_terraform_command(
                "apply", temp_dir,
                capture_output=True,
                no_color=IsFlagged,
                skip_plan=True
            )
            
            if return_code != 0:
                raise Exception(f"Terraform apply failed: {stderr or stdout}")
            
            # Get outputs
            return_code, stdout, stderr = self._run_terraform_command(
                "output", temp_dir,
                capture_output=True,
                no_color=IsFlagged,
                json=True
            )
            
            if return_code != 0:
                raise Exception(f"Terraform output failed: {stderr or stdout}")
            
            outputs = json.loads(stdout)
            
            # Destroy temporary directory
            shutil.rmtree(temp_dir)
            
            return {
                "success": True,
                "outputs": outputs,
                "loadbalancer_name": loadbalancer_name,
                "instance_name": instance_name,
                "region": region or self.settings.huawei_region,
            }
            
        except Exception as e:
            logger.error(f"Error deploying ELB: {e}")
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "success": False,
                "error": str(e),
                "loadbalancer_name": loadbalancer_name,
            }
    
    def destroy_resources(self, module_type: str, resource_name: str) -> Dict[str, Any]:
        """Destroy Terraform resources"""
        # This would require tracking state files - for simplicity, we'll skip for now
        # In a production system, you'd need to manage state files properly
        return {
            "success": True,
            "message": f"Destroy functionality for {module_type} '{resource_name}' would be implemented with proper state management"
        }