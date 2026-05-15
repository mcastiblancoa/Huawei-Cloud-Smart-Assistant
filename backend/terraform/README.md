# Terraform Integration for Huawei Cloud Smart Assistant

This directory contains Terraform modules and tools for deploying Huawei Cloud resources through the LangGraph-based smart assistant.

## Overview

The Terraform integration provides reliable deployment of Huawei Cloud resources that may have issues with KooCLI, specifically:

1. **OBS (Object Storage Service)** buckets with KMS encryption
2. **ELB (Elastic Load Balancer)** complete environments with VPC, subnet, security groups, ECS instances, and EIPs

## Directory Structure

```
terraform/
├── modules/
│   ├── obs/
│   │   ├── main.tf          # OBS bucket with KMS encryption
│   │   ├── variables.tf     # Input variables for OBS
│   │   └── outputs.tf       # Output values for OBS
│   └── elb/
│       ├── main.tf          # Complete ELB environment
│       ├── variables.tf     # Input variables for ELB
│       └── outputs.tf       # Output values for ELB
├── example_variables.tfvars.json  # Example variables file
└── README.md                # This file
```

## Modules

### OBS Module

Creates an OBS bucket with optional KMS encryption.

**Features:**
- Creates OBS bucket with configurable storage class
- Optional KMS encryption (create new key or use existing)
- Configurable ACL (private, public-read, etc.)
- Force destroy option
- Tagging support

**Usage Example:**
```hcl
module "obs_bucket" {
  source = "./modules/obs"
  
  region_name = "ap-southeast-3"
  access_key  = "your-access-key"
  secret_key  = "your-secret-key"
  
  bucket_name = "my-terraform-bucket"
  bucket_storage_class = "STANDARD"
  bucket_acl = "private"
  bucket_encryption = true
  key_alias = "my-obs-key"
  bucket_tags = {
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}
```

### ELB Module

Creates a complete ELB environment including:
- VPC and subnet
- Security group
- ECS instance
- ELB load balancer
- Listener and backend pool
- Health check
- Optional EIP association

**Features:**
- Complete infrastructure as code
- Configurable listener protocols (HTTP, HTTPS, TCP, UDP)
- Health checks with configurable parameters
- Optional EIP with configurable bandwidth
- Support for HTTPS with SSL certificates

**Usage Example:**
```hcl
module "elb_environment" {
  source = "./modules/elb"
  
  region_name = "ap-southeast-3"
  access_key  = "your-access-key"
  secret_key  = "your-secret-key"
  
  vpc_name = "tf-vpc"
  subnet_name = "tf-subnet"
  security_group_name = "tf-sg"
  loadbalancer_name = "tf-elb"
  instance_name = "tf-ecs"
  
  is_associate_eip = true
  bandwidth_name = "tf-eip-bw"
  bandwidth_size = 5
  
  listener_protocol = "HTTP"
  listener_port = 80
  pool_protocol = "HTTP"
  pool_method = "ROUND_ROBIN"
  
  health_check_type = "HTTP"
  health_check_expected_codes = "200-202"
  health_check_url_path = "/"
  health_check_http_method = "GET"
}
```

## Python Integration

The Terraform integration is exposed through Python tools in `tools/terraform_tools.py`:

### Available Tools

1. **`deploy_obs_bucket_with_terraform`** - Deploy OBS bucket with Terraform
   ```python
   deploy_obs_bucket_with_terraform(
       bucket_name="my-bucket",
       region="ap-southeast-3",
       storage_class="STANDARD",
       encryption=True,
       key_alias="my-kms-key"
   )
   ```

2. **`deploy_elb_with_terraform`** - Deploy complete ELB environment
   ```python
   deploy_elb_with_terraform(
       loadbalancer_name="my-elb",
       vpc_name="my-vpc",
       subnet_name="my-subnet",
       security_group_name="my-sg",
       instance_name="my-ecs",
       associate_eip=True,
       listener_protocol="HTTP"
   )
   ```

3. **`list_terraform_deployments`** - List Terraform deployments (placeholder)

### TerraformManager Class

The `TerraformManager` class in `tools/terraform_manager.py` handles:
- Temporary directory management for Terraform state
- Dynamic generation of Terraform configuration
- Execution of Terraform commands (init, plan, apply)
- Output parsing and error handling

## Authentication

Credentials are automatically loaded from the application settings (`config/settings.py`):
- `HUAWEI_AK` - Access Key
- `HUAWEI_SK` - Secret Key  
- `HUAWEI_REGION` - Default region

## Benefits over KooCLI

1. **Reliability**: Terraform provides better error handling and idempotency
2. **Declarative**: Infrastructure as code approach
3. **State Management**: Track resource state and dependencies
4. **Complex Deployments**: Handle multi-resource deployments atomically
5. **Rollback**: Better handling of failed deployments

## Usage in LangGraph

The Terraform tools are registered in the `ToolRegistry` and can be used by the LangGraph agent:

```python
# The tools are automatically loaded and available to the agent
# Users can ask: "Create an OBS bucket with Terraform"
# or "Deploy an ELB with Terraform"
```

## Testing

To test the Terraform modules manually:

```bash
cd terraform/modules/obs
terraform init
terraform plan -var-file="../../example_variables.tfvars.json"
terraform apply -var-file="../../example_variables.tfvars.json"
```

## Notes

- Terraform state files are managed in temporary directories (not persisted)
- For production use, consider implementing state file persistence
- The modules use the official HuaweiCloud Terraform provider
- All resources follow Huawei Cloud best practices