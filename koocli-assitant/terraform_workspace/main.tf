
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
  access_key = "HPUAMRFMN62OKUTHAXTT"
  secret_key = "W2oamhPOOeqOoJeTyD7v2wRRHpyqx8YfzseaK859"
}

# ============================================================================
# ARQUITECTURA WEB CON LOAD BALANCER
# ============================================================================

# --- VPC y Subnet ---
resource "huaweicloud_vpc" "prod_vpc" {
  name = "prod-vpc-web"
  cidr = "10.0.0.0/16"
}

resource "huaweicloud_vpc_subnet" "prod_subnet" {
  name        = "prod-subnet-web"
  cidr        = "10.0.1.0/24"
  gateway_ip  = "10.0.1.1"
  vpc_id      = huaweicloud_vpc.prod_vpc.id
  availability_zone = "ap-southeast-3a"
}

# --- Security Group ---
resource "huaweicloud_networking_secgroup" "web_sg" {
  name        = "web-sg-lb"
  description = "Security group for web servers - HTTP traffic"
  delete_default_rules = false
}

resource "huaweicloud_networking_secgroup_rule" "allow_http" {
  security_group_id = huaweicloud_networking_secgroup.web_sg.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_networking_secgroup_rule" "allow_ssh" {
  security_group_id = huaweicloud_networking_secgroup.web_sg.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = "0.0.0.0/0"
}

# --- ECS Instances ---
data "huaweicloud_images_image" "ubuntu" {
  name_regex  = "^Ubuntu 22.04 server 64bit"
  most_recent = true
}

resource "huaweicloud_compute_instance" "web_node_1" {
  name               = "web-node-1"
  image_id           = data.huaweicloud_images_image.ubuntu.id
  flavor_id          = "s6.large.2"
  security_group_ids = [huaweicloud_networking_secgroup.web_sg.id]
  availability_zone  = "ap-southeast-3a"
  system_disk_type   = "SAS"
  system_disk_size   = 40

  network {
    uuid = huaweicloud_vpc_subnet.prod_subnet.id
  }
  
  tags = {
    Name = "web-node-1"
    Role = "web-server"
  }
}

resource "huaweicloud_compute_instance" "web_node_2" {
  name               = "web-node-2"
  image_id           = data.huaweicloud_images_image.ubuntu.id
  flavor_id          = "s6.large.2"
  security_group_ids = [huaweicloud_networking_secgroup.web_sg.id]
  availability_zone  = "ap-southeast-3a"
  system_disk_type   = "SAS"
  system_disk_size   = 40

  network {
    uuid = huaweicloud_vpc_subnet.prod_subnet.id
  }
  
  tags = {
    Name = "web-node-2"
    Role = "web-server"
  }
}

# --- Load Balancer (ELB) ---
resource "huaweicloud_lb_loadbalancer" "web_lb" {
  name           = "web-loadbalancer"
  vip_subnet_id  = huaweicloud_vpc_subnet.prod_subnet.id
  
  tags = {
    Name = "web-loadbalancer"
  }
}

# --- Elastic IP (EIP) ---
resource "huaweicloud_vpc_eip" "elb_eip" {
  publicip {
    type = "5_bgp"
  }

  bandwidth {
    share_type  = "PER"
    name        = "elb-bandwidth"
    size        = 10
    charge_mode = "traffic"
  }
}

# --- Associate EIP to Load Balancer ---
resource "huaweicloud_vpc_eip_associate" "elb_eip_associate" {
  public_ip = huaweicloud_vpc_eip.elb_eip.address
  port_id   = huaweicloud_lb_loadbalancer.web_lb.vip_port_id
}

# --- Listener (Port 80) ---
resource "huaweicloud_lb_listener" "http_listener" {
  name            = "http-listener"
  protocol        = "HTTP"
  protocol_port   = 80
  loadbalancer_id = huaweicloud_lb_loadbalancer.web_lb.id
  default_pool_id = huaweicloud_lb_pool.web_pool.id
}

# --- Backend Pool ---
resource "huaweicloud_lb_pool" "web_pool" {
  name            = "web-pool"
  protocol        = "HTTP"
  lb_method       = "ROUND_ROBIN"
  loadbalancer_id = huaweicloud_lb_loadbalancer.web_lb.id
  
  persistence {
    type = "SOURCE_IP"
  }
}

# --- Backend Members (ECS instances) ---
resource "huaweicloud_lb_member" "member_1" {
  address       = huaweicloud_compute_instance.web_node_1.access_ip_v4
  protocol_port = 80
  pool_id       = huaweicloud_lb_pool.web_pool.id
  subnet_id     = huaweicloud_vpc_subnet.prod_subnet.id
}

resource "huaweicloud_lb_member" "member_2" {
  address       = huaweicloud_compute_instance.web_node_2.access_ip_v4
  protocol_port = 80
  pool_id       = huaweicloud_lb_pool.web_pool.id
  subnet_id     = huaweicloud_vpc_subnet.prod_subnet.id
}

# --- Outputs ---
output "load_balancer_public_ip" {
  value       = huaweicloud_vpc_eip.elb_eip.address
  description = "Public IP of the Load Balancer"
}

output "web_node_1_private_ip" {
  value = huaweicloud_compute_instance.web_node_1.access_ip_v4
}

output "web_node_2_private_ip" {
  value = huaweicloud_compute_instance.web_node_2.access_ip_v4
}