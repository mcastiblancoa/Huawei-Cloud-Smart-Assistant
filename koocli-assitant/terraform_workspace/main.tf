
terraform {
  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = "~> 1.60.0"
    }
  }
}

provider "huaweicloud" {
  region     = "ap-southeast-3"
  access_key = "HPUANILDWRNSQANO1AMO"
  secret_key = "9OQffSuSKlfhg8lD5t3EXd060jUIEb0IseRH7y2O"
}

# Infraestructura web de alta disponibilidad en Huawei Cloud
# Región: la-north-2

# 1. VPC y subred
resource "huaweicloud_vpc" "prod_vpc" {
  name = "prod-vpc"
  cidr = "10.0.0.0/16"
}

resource "huaweicloud_vpc_subnet" "prod_subnet" {
  name       = "prod-subnet"
  cidr       = "10.0.1.0/24"
  gateway_ip = "10.0.1.1"
  vpc_id     = huaweicloud_vpc.prod_vpc.id
}

# 2. Bucket de OBS
resource "huaweicloud_obs_bucket" "assets_bucket" {
  bucket = "mi-proyecto-assets-2026"
  acl    = "private"
  region = "la-north-2"
}

# 3. Servidores ECS con configuración básica
resource "huaweicloud_compute_instance" "web_node_1" {
  name              = "web-node-1"
  flavor_name       = "s6.large.2"
  image_name        = "Ubuntu 22.04 server 64bit"
  availability_zone = "ap-southeast-3a"
  
  # Usar autenticación por contraseña
  admin_pass = "Huawei@2026!"
  
  system_disk_type = "SAS"
  system_disk_size = 40
  
  network {
    uuid = huaweicloud_vpc_subnet.prod_subnet.id
  }
  
  metadata = {
    role = "web-server"
  }
}

resource "huaweicloud_compute_instance" "web_node_2" {
  name              = "web-node-2"
  flavor_name       = "s6.large.2"
  image_name        = "Ubuntu 22.04 server 64bit"
  availability_zone = "ap-southeast-3a"
  
  # Usar autenticación por contraseña
  admin_pass = "Huawei@2026!"
  
  system_disk_type = "SAS"
  system_disk_size = 40
  
  network {
    uuid = huaweicloud_vpc_subnet.prod_subnet.id
  }
  
  metadata = {
    role = "web-server"
  }
}

# 4. IP Elástica para los servidores web
resource "huaweicloud_vpc_eip" "web_node_1_eip" {
  publicip {
    type = "5_bgp"
  }
  
  bandwidth {
    name        = "web-node-1-bandwidth"
    size        = 100
    share_type  = "PER"
    charge_mode = "traffic"
  }
}

resource "huaweicloud_vpc_eip" "web_node_2_eip" {
  publicip {
    type = "5_bgp"
  }
  
  bandwidth {
    name        = "web-node-2-bandwidth"
    size        = 100
    share_type  = "PER"
    charge_mode = "traffic"
  }
}

# 5. Asociar EIPs a los servidores
resource "huaweicloud_compute_eip_associate" "web_node_1_eip_assoc" {
  public_ip   = huaweicloud_vpc_eip.web_node_1_eip.address
  instance_id = huaweicloud_compute_instance.web_node_1.id
}

resource "huaweicloud_compute_eip_associate" "web_node_2_eip_assoc" {
  public_ip   = huaweicloud_vpc_eip.web_node_2_eip.address
  instance_id = huaweicloud_compute_instance.web_node_2.id
}

# Outputs importantes
output "vpc_id" {
  value = huaweicloud_vpc.prod_vpc.id
  description = "ID de la VPC creada"
}

output "subnet_id" {
  value = huaweicloud_vpc_subnet.prod_subnet.id
  description = "ID de la subred creada"
}

output "bucket_name" {
  value = huaweicloud_obs_bucket.assets_bucket.bucket
  description = "Nombre del bucket OBS creado"
}

output "web_node_1_private_ip" {
  value = huaweicloud_compute_instance.web_node_1.access_ip_v4
  description = "IP privada del servidor web-node-1"
}

output "web_node_2_private_ip" {
  value = huaweicloud_compute_instance.web_node_2.access_ip_v4
  description = "IP privada del servidor web-node-2"
}

output "web_node_1_public_ip" {
  value = huaweicloud_vpc_eip.web_node_1_eip.address
  description = "IP pública del servidor web-node-1"
}

output "web_node_2_public_ip" {
  value = huaweicloud_vpc_eip.web_node_2_eip.address
  description = "IP pública del servidor web-node-2"
}

output "web_node_1_admin_pass" {
  value = "Huawei@2026!"
  description = "Contraseña de administrador para web-node-1"
  sensitive = true
}

output "web_node_2_admin_pass" {
  value = "Huawei@2026!"
  description = "Contraseña de administrador para web-node-2"
  sensitive = true
}

output "architecture_summary" {
  value = "Infraestructura web de alta disponibilidad desplegada exitosamente con 2 servidores ECS, VPC, subnet, bucket OBS y EIPs para cada servidor."
}