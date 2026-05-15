import json
import re
from typing import Optional, Dict, Any
from langchain_core.tools import tool

from tools.terraform_manager import TerraformManager
from tools.registry import ToolMeta, ToolCategory
from config.logging import get_logger

logger = get_logger("tools.terraform_tools")


@tool
def deploy_obs_bucket_with_terraform(
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
    tags: Optional[str] = None
) -> str:
    """Deploy an OBS (Object Storage Service) bucket using Terraform.
    
    This tool creates a complete OBS bucket with KMS encryption using Terraform,
    which is more reliable than KooCLI for OBS operations.
    
    Args:
        bucket_name: The name of the OBS bucket (required, must be globally unique).
        region: Huawei Cloud region (default: from settings).
        storage_class: Storage class: STANDARD, WARM, COLD (default: STANDARD).
        acl: Access control: private, public-read, public-read-write, public-read-delivered, public-read-write-delivered (default: private).
        encryption: Enable server-side encryption (default: true).
        sse_algorithm: Encryption algorithm: kms (default: kms).
        encryption_key_id: Existing KMS key ID (optional, creates new key if not provided).
        key_alias: Alias for the KMS key (required if encryption_key_id is not provided).
        key_usage: KMS key usage: ENCRYPT_DECRYPT (default).
        force_destroy: Force destroy bucket even if it contains objects (default: true).
        tags: JSON string of tags for the bucket (e.g., '{"Environment": "Production", "Project": "MyProject"}').
    """
    try:
        # Parse tags if provided
        tags_dict = {}
        if tags:
            try:
                tags_dict = json.loads(tags)
            except json.JSONDecodeError:
                # Try to parse as key=value pairs
                tags_dict = {}
                for pair in tags.split(','):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        tags_dict[key.strip()] = value.strip()
        
        # Create Terraform manager
        tf_manager = TerraformManager()
        
        # Deploy OBS bucket
        result = tf_manager.deploy_obs_bucket(
            bucket_name=bucket_name,
            region=region,
            storage_class=storage_class,
            acl=acl,
            encryption=encryption,
            sse_algorithm=sse_algorithm,
            encryption_key_id=encryption_key_id,
            key_alias=key_alias or f"obs-key-{bucket_name}",
            key_usage=key_usage,
            force_destroy=force_destroy,
            tags=tags_dict
        )
        
        if result["success"]:
            outputs = result.get("outputs", {}).get("all_outputs", {}).get("value", {})
            
            response = f"""✅ **OBS Bucket created successfully using Terraform!**

**Bucket Details:**
- **Name:** {bucket_name}
- **Region:** {result.get('region', 'N/A')}
- **Storage Class:** {storage_class}
- **ACL:** {acl}
- **Encryption:** {'Enabled' if encryption else 'Disabled'}
- **SSE Algorithm:** {sse_algorithm if encryption else 'N/A'}

**Outputs:**
- Bucket Domain Name: {outputs.get('bucket_domain_name', 'N/A')}
- Bucket ID: {outputs.get('bucket_id', 'N/A')}
- KMS Key ID: {outputs.get('kms_key_id', 'N/A') if encryption else 'N/A'}

**Terraform Deployment:** Successfully provisioned using infrastructure as code."""
            
            if tags_dict:
                response += f"\n**Tags:** {json.dumps(tags_dict)}"
            
            return response
        else:
            return f"""❌ **Failed to create OBS bucket using Terraform**

**Error:** {result.get('error', 'Unknown error')}

**Bucket Details:**
- Name: {bucket_name}
- Region: {region or 'Default from settings'}

**Terraform Deployment:** Failed. Please check the error message above."""
            
    except Exception as e:
        logger.error(f"Error in deploy_obs_bucket_with_terraform: {e}")
        return f"""❌ **Error creating OBS bucket with Terraform**

**Error:** {str(e)}

**Bucket Details:**
- Name: {bucket_name}
- Region: {region or 'Default from settings'}

**Note:** This tool uses Terraform for reliable OBS deployment, as KooCLI may have issues with OBS operations."""


@tool
def deploy_elb_with_terraform(
    loadbalancer_name: str,
    vpc_name: str,
    subnet_name: str,
    security_group_name: str,
    instance_name: str,
    region: Optional[str] = None,
    availability_zone: Optional[str] = None,
    instance_flavor: Optional[str] = None,
    instance_cpu_cores: int = 2,
    instance_memory_gb: int = 4,
    instance_image_id: Optional[str] = None,
    vpc_cidr: str = "172.16.0.0/16",
    associate_eip: bool = True,
    eip_bandwidth_name: Optional[str] = None,
    eip_bandwidth_size: int = 5,
    listener_protocol: str = "HTTP",
    listener_port: int = 80,
    pool_algorithm: str = "ROUND_ROBIN",
    health_check_type: str = "HTTP",
    health_check_path: str = "/",
    health_check_method: str = "GET"
) -> str:
    """Deploy a complete ELB (Elastic Load Balancer) environment using Terraform.
    
    This tool creates: VPC, Subnet, Security Group, ECS instance, ELB, Listener, Pool, 
    Health Check, and optionally an EIP - all using Terraform for reliable deployment.
    
    Args:
        loadbalancer_name: Name for the ELB load balancer (required).
        vpc_name: Name for the VPC (required).
        subnet_name: Name for the subnet (required).
        security_group_name: Name for the security group (required).
        instance_name: Name for the ECS instance (required).
        region: Huawei Cloud region (default: from settings).
        availability_zone: Availability zone (e.g., 'ap-southeast-3a').
        instance_flavor: ECS instance flavor ID (optional, auto-selects if not provided).
        instance_cpu_cores: Number of CPU cores (default: 2).
        instance_memory_gb: Memory size in GB (default: 4).
        instance_image_id: Image ID for ECS instance (optional, uses default Ubuntu).
        vpc_cidr: VPC CIDR block (default: 172.16.0.0/16).
        associate_eip: Whether to associate an EIP with the ELB (default: true).
        eip_bandwidth_name: Name for EIP bandwidth (optional).
        eip_bandwidth_size: EIP bandwidth size in Mbps (default: 5).
        listener_protocol: Listener protocol: HTTP, HTTPS, TCP, UDP (default: HTTP).
        listener_port: Listener port (default: 80).
        pool_algorithm: Load balancing algorithm: ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP (default: ROUND_ROBIN).
        health_check_type: Health check type: HTTP, TCP, UDP_CONNECT (default: HTTP).
        health_check_path: Health check URL path (default: /).
        health_check_method: Health check HTTP method: GET, HEAD, POST (default: GET).
    """
    try:
        # Create Terraform manager
        tf_manager = TerraformManager()
        
        # Determine instance flavor ID based on CPU and memory
        instance_flavor_id = instance_flavor
        if not instance_flavor_id:
            # Map CPU/memory to common flavors
            if instance_cpu_cores == 1 and instance_memory_gb == 1:
                instance_flavor_id = "s6.small.1"
            elif instance_cpu_cores == 1 and instance_memory_gb == 2:
                instance_flavor_id = "s6.medium.2"
            elif instance_cpu_cores == 2 and instance_memory_gb == 4:
                instance_flavor_id = "s6.large.2"
            elif instance_cpu_cores == 4 and instance_memory_gb == 8:
                instance_flavor_id = "s6.xlarge.2"
            else:
                instance_flavor_id = "s6.large.2"  # Default
        
        # Determine health check expected codes based on protocol
        health_check_expected_codes = "200-202"
        if listener_protocol.upper() != "HTTP" and listener_protocol.upper() != "HTTPS":
            health_check_expected_codes = None
        
        # Deploy ELB
        result = tf_manager.deploy_elb(
            loadbalancer_name=loadbalancer_name,
            vpc_name=vpc_name,
            subnet_name=subnet_name,
            security_group_name=security_group_name,
            instance_name=instance_name,
            region=region,
            availability_zone=availability_zone,
            instance_flavor_id=instance_flavor_id,
            instance_flavor_cpu_core_count=instance_cpu_cores,
            instance_flavor_memory_size=instance_memory_gb,
            instance_image_id=instance_image_id,
            vpc_cidr=vpc_cidr,
            is_associate_eip=associate_eip,
            bandwidth_name=eip_bandwidth_name or f"{loadbalancer_name}-bandwidth",
            bandwidth_size=eip_bandwidth_size,
            listener_protocol=listener_protocol.upper(),
            listener_port=listener_port,
            pool_protocol=listener_protocol.upper(),
            pool_method=pool_algorithm.upper(),
            member_protocol_port=listener_port,
            health_check_type=health_check_type.upper(),
            health_check_expected_codes=health_check_expected_codes,
            health_check_url_path=health_check_path,
            health_check_http_method=health_check_method.upper()
        )
        
        if result["success"]:
            outputs = result.get("outputs", {}).get("all_outputs", {}).get("value", {})
            
            response = f"""✅ **ELB Environment created successfully using Terraform!**

**Infrastructure Details:**
- **ELB Name:** {loadbalancer_name}
- **Region:** {result.get('region', 'N/A')}
- **Availability Zone:** {availability_zone or 'Auto-selected'}

**Resources Created:**
1. **VPC:** {vpc_name} (CIDR: {vpc_cidr})
2. **Subnet:** {subnet_name}
3. **Security Group:** {security_group_name}
4. **ECS Instance:** {instance_name} (Flavor: {instance_flavor_id})
5. **ELB Load Balancer:** {loadbalancer_name}
6. **Listener:** {listener_protocol}:{listener_port}
7. **Backend Pool:** {pool_algorithm} algorithm
8. **Health Check:** {health_check_type} on path '{health_check_path}'
9. **EIP:** {'Yes' if associate_eip else 'No'}

**Outputs:**
- ELB ID: {outputs.get('loadbalancer_id', 'N/A')}
- ECS Instance ID: {outputs.get('ecs_instance_id', 'N/A')}
- ECS Instance IP: {outputs.get('ecs_instance_ip', 'N/A')}
- EIP Address: {outputs.get('eip_address', 'Not associated')}
- VPC ID: {outputs.get('vpc_id', 'N/A')}
- Subnet ID: {outputs.get('subnet_id', 'N/A')}
- Security Group ID: {outputs.get('security_group_id', 'N/A')}

**Access Information:**
- **ELB Endpoint:** {outputs.get('eip_address', 'Configured but no public IP') if associate_eip else 'Internal only'}
- **Backend Server:** {outputs.get('ecs_instance_ip', 'N/A')}:{listener_port}

**Terraform Deployment:** Successfully provisioned complete infrastructure as code."""
            
            return response
        else:
            return f"""❌ **Failed to create ELB environment using Terraform**

**Error:** {result.get('error', 'Unknown error')}

**Infrastructure Details:**
- ELB Name: {loadbalancer_name}
- Region: {region or 'Default from settings'}
- VPC: {vpc_name}
- Subnet: {subnet_name}
- ECS Instance: {instance_name}

**Terraform Deployment:** Failed. Please check the error message above."""
            
    except Exception as e:
        logger.error(f"Error in deploy_elb_with_terraform: {e}")
        return f"""❌ **Error creating ELB environment with Terraform**

**Error:** {str(e)}

**Infrastructure Details:**
- ELB Name: {loadbalancer_name}
- Region: {region or 'Default from settings'}

**Note:** This tool uses Terraform for reliable ELB deployment, as KooCLI may have issues with complex ELB configurations."""


@tool
def list_terraform_deployments() -> str:
    """List all Terraform deployments and their status.
    
    This tool shows information about Terraform-managed resources.
    Note: This is a placeholder - in a real implementation, you would
    track Terraform state files to provide actual deployment information.
    """
    try:
        # In a real implementation, you would read Terraform state files
        # For now, we'll return a placeholder response
        
        response = """📋 **Terraform Deployment Status**

**Note:** This is a placeholder implementation. In a production system, 
Terraform state files would be tracked to show actual deployments.

**How Terraform Integration Works:**
1. **OBS Deployments:** Uses Terraform to create OBS buckets with KMS encryption
2. **ELB Deployments:** Uses Terraform to create complete ELB environments
3. **State Management:** Each deployment creates temporary Terraform state
4. **Reliability:** More reliable than KooCLI for complex resource deployments

**Available Terraform Modules:**
1. **OBS Module:** Creates OBS buckets with optional KMS encryption
2. **ELB Module:** Creates VPC, subnet, security group, ECS instance, ELB, listener, pool, health check, and EIP

**To deploy resources:**
- Use `deploy_obs_bucket_with_terraform` for OBS buckets
- Use `deploy_elb_with_terraform` for ELB environments

**Benefits over KooCLI:**
- Declarative infrastructure as code
- Better error handling and rollback
- Consistent resource creation
- Support for complex dependencies
- State tracking (when implemented)"""
        
        return response
        
    except Exception as e:
        logger.error(f"Error in list_terraform_deployments: {e}")
        return f"Error listing Terraform deployments: {str(e)}"


TERRAFORM_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=deploy_obs_bucket_with_terraform,
        service="TERRAFORM",
        category=ToolCategory.DEPLOY,
        keywords=[
            "terraform obs", "terraform bucket", "create obs terraform",
            "desplegar obs terraform", "obs terraform", "bucket terraform",
            "kms encryption terraform", "almacenamiento objeto terraform"
        ],
        is_read_only=False,
        cacheable=False,
    ),
    ToolMeta(
        tool=deploy_elb_with_terraform,
        service="TERRAFORM",
        category=ToolCategory.DEPLOY,
        keywords=[
            "terraform elb", "terraform load balancer", "create elb terraform",
            "desplegar elb terraform", "elb terraform", "load balancer terraform",
            "balanceador carga terraform", "vpc terraform", "ecs terraform"
        ],
        is_read_only=False,
        cacheable=False,
    ),
    ToolMeta(
        tool=list_terraform_deployments,
        service="TERRAFORM",
        category=ToolCategory.QUERY,
        keywords=[
            "list terraform", "terraform status", "terraform deployments",
            "terraform resources", "estado terraform", "despliegues terraform"
        ],
        is_read_only=True,
        cacheable=True,
        cache_ttl=30,
    ),
]