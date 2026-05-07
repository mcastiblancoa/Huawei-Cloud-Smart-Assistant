import json
import re
import time
from typing import Optional

from langchain_core.tools import tool

from koocli.executor import execute_koocli
from utils.sanitize import sanitize_params
from config.logging import get_logger

logger = get_logger("tools.deploy")

REGION_DEFAULTS = {
    "ap-southeast-3": {
        "vpc_id": "28ea9627-edb0-4b94-a6eb-051d0dcfabcf",
        "subnet_id": "10e9345f-63c6-4d99-a0c7-a75ecb88d0f3",
        "image_id": "1c136556-5a40-4382-884a-eb340532dc58",
        "az": "ap-southeast-3a",
    },
    "la-north-2": {
        "vpc_id": "41d89d5c-9f93-43c7-9e41-a67e46f74fae",
        "subnet_id": "6fd217ab-bfae-4587-a786-f0f6991bdec9",
        "image_id": "",
        "az": "la-north-2a",
    },
}


def _resolve_defaults(region: str, vpc_id: str, subnet_id: str, image_id: str, az: str):
    defaults = REGION_DEFAULTS.get(region, {})
    return {
        "vpc_id": vpc_id or defaults.get("vpc_id", ""),
        "subnet_id": subnet_id or defaults.get("subnet_id", ""),
        "image_id": image_id or defaults.get("image_id", ""),
        "az": az or defaults.get("az", ""),
    }


def _extract_id(result: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, result)
        if match:
            return match.group(1)
    return ""


@tool
def deploy_elb_loadbalancer(
    name: str,
    region: str = "ap-southeast-3",
    availability_zone: str = "ap-southeast-3a",
    vpc_id: str = "",
    subnet_id: str = "",
    guaranteed: bool = True,
    public_ip: bool = False,
    bandwidth_size: int = 5,
    bandwidth_charge_mode: str = "traffic",
    publicip_pool_name: str = "",
) -> str:
    """Deploys an ELB Load Balancer on Huawei Cloud with validated parameters.
    Use this tool INSTEAD of run_koocli_command for creating load balancers.
    It handles parameter construction and validation automatically.

    Args:
        name: Name for the load balancer (required).
        region: Huawei Cloud region, e.g. 'ap-southeast-3', 'la-north-2'.
        availability_zone: AZ for the load balancer, e.g. 'ap-southeast-3a'.
        vpc_id: VPC ID to attach to (required for dedicated ELB).
        subnet_id: Subnet ID. If empty, uses default subnet.
        guaranteed: True for dedicated (default, recommended), False for shared.
        public_ip: True to assign a public EIP. Requires publicip_pool_name in some regions.
        bandwidth_size: Bandwidth size in Mbit/s for the EIP (default 5).
        bandwidth_charge_mode: 'traffic' (pay-by-traffic) or 'bandwidth' (pay-by-bandwidth).
        publicip_pool_name: EIP pool name (required in some regions for public IP).
    """
    name = sanitize_params({"n": name})["n"]

    defaults = _resolve_defaults(region, vpc_id, subnet_id, "", availability_zone)
    if not vpc_id:
        vpc_id = defaults["vpc_id"]
    if not subnet_id:
        subnet_id = defaults["subnet_id"]
    if not availability_zone:
        availability_zone = defaults["az"]

    loadbalancer = {
        "name": name,
        "guaranteed": str(guaranteed).lower(),
        "availability_zone_list": [availability_zone],
    }

    if vpc_id:
        loadbalancer["vpc_id"] = vpc_id
    if subnet_id:
        loadbalancer["elb_virsubnet_ids"] = [subnet_id]

    if public_ip:
        publicip = {
            "bandwidth": {
                "size": str(bandwidth_size),
                "charge_mode": bandwidth_charge_mode,
            }
        }
        if publicip_pool_name:
            publicip["publicip_pool_name"] = publicip_pool_name
        loadbalancer["publicip"] = publicip

    params = {
        "cli-region": region,
        "loadbalancer": loadbalancer,
    }

    logger.info(
        "Deploying ELB load balancer",
        extra={"structured_extra": {
            "name": name,
            "region": region,
            "az": availability_zone,
            "guaranteed": guaranteed,
            "public_ip": public_ip,
        }},
    )

    result = execute_koocli("ELB", "CreateLoadBalancer", params)

    return result


@tool
def deploy_ecs_instance(
    name: str,
    region: str = "ap-southeast-3",
    availability_zone: str = "",
    flavor: str = "s6.small.1",
    image_id: str = "",
    vpc_id: str = "",
    subnet_id: str = "",
    root_volume_type: str = "SAS",
    root_volume_size: int = 40,
    admin_pass: str = "",
) -> str:
    """Deploys an ECS (Elastic Cloud Server) instance on Huawei Cloud.
    Use this tool INSTEAD of run_koocli_command for creating ECS instances.
    It handles parameter construction, validation, and region defaults automatically.
    Uses CreatePostPaidServers API which returns the server directly (no job_id polling).

    Args:
        name: Server name (required).
        region: Huawei Cloud region.
        availability_zone: AZ, e.g. 'ap-southeast-3a'. Auto-resolved if empty.
        flavor: Instance flavor, e.g. 's6.small.1', 's6.medium.2'.
        image_id: Image ID. Auto-resolved per region if empty.
        vpc_id: VPC ID. Auto-resolved per region if empty.
        subnet_id: Subnet ID. Auto-resolved per region if empty.
        root_volume_type: Root disk type: 'SAS', 'SSD', 'GPSSD', 'ESSD'.
        root_volume_size: Root disk size in GB (default 40).
        admin_pass: Admin password. If empty, auto-generated.
    """
    defaults = _resolve_defaults(region, vpc_id, subnet_id, image_id, availability_zone)
    resolved_vpc = defaults["vpc_id"]
    resolved_subnet = defaults["subnet_id"]
    resolved_image = defaults["image_id"]
    resolved_az = defaults["az"]

    if not resolved_image:
        resolved_image = "Ubuntu 22.04 server 64bit"

    if not admin_pass:
        admin_pass = f"Huawei@{int(time.time()) % 100000}!"

    server = {
        "name": name,
        "flavorRef": flavor,
        "availability_zone": resolved_az,
        "imageRef": resolved_image,
        "root_volume": {
            "volume_type": root_volume_type,
            "size": root_volume_size,
        },
        "adminPass": admin_pass,
    }

    if resolved_vpc:
        server["vpcid"] = resolved_vpc
    if resolved_subnet:
        server["nics"] = [{"subnet_id": resolved_subnet}]

    params = {
        "cli-region": region,
        "server": server,
    }

    logger.info(
        "Deploying ECS instance",
        extra={"structured_extra": {
            "name": name, "region": region, "flavor": flavor,
            "vpc_id": resolved_vpc, "subnet_id": resolved_subnet,
            "image_id": resolved_image, "az": resolved_az,
        }},
    )

    result = execute_koocli("ECS", "CreatePostPaidServers", params)

    if "Error" in result:
        return f"ECS creation FAILED.\n{result}"

    server_id = _extract_id(result, [
        r'"id":\s*"([^"]+)"',
        r'"server_id":\s*"([^"]+)"',
    ])

    if server_id:
        time.sleep(8)
        detail = execute_koocli("ECS", "ShowServer", {
            "cli-region": region,
            "server_id": server_id,
        })
        private_ip = _extract_id(detail, [
            r'"ip_address":\s*"(\d+\.\d+\.\d+\.\d+)"',
        ])
        status = "ACTIVE" if '"status":"ACTIVE"' in detail or '"ACTIVE"' in detail else "BUILD"

        ip_info = f" | Private IP: {private_ip}" if private_ip else ""
        return (
            f"ECS instance '{name}' created SUCCESSFULLY.\n"
            f"Server ID: {server_id}\n"
            f"Status: {status}{ip_info}\n"
            f"Region: {region} | AZ: {resolved_az} | Flavor: {flavor}"
        )

    return f"ECS creation response:\n{result}"


@tool
def deploy_vpc(
    name: str,
    cidr: str = "10.0.0.0/16",
    region: str = "ap-southeast-3",
) -> str:
    """Deploys a VPC (Virtual Private Cloud) on Huawei Cloud.
    Use this tool INSTEAD of run_koocli_command for creating VPCs.

    Args:
        name: VPC name (required).
        cidr: VPC CIDR block (default '10.0.0.0/16').
        region: Huawei Cloud region.
    """
    params = {
        "cli-region": region,
        "vpc": {
            "name": name,
            "cidr": cidr,
        },
    }

    logger.info(
        "Deploying VPC",
        extra={"structured_extra": {"name": name, "cidr": cidr, "region": region}},
    )

    return execute_koocli("VPC", "CreateVpc", params)


@tool
def deploy_full_stack(
    ecs_name: str,
    elb_name: str,
    region: str = "ap-southeast-3",
    availability_zone: str = "",
    flavor: str = "s6.small.1",
    image_id: str = "",
    vpc_id: str = "",
    subnet_id: str = "",
    root_volume_type: str = "SAS",
    root_volume_size: int = 40,
    elb_public_ip: bool = True,
    listener_protocol: str = "HTTP",
    listener_port: int = 80,
    pool_algorithm: str = "ROUND_ROBIN",
    admin_pass: str = "",
) -> str:
    """Deploys a complete stack: ECS + ELB + Listener + Pool + Member + EIP in one call.
    Use this tool when the user wants to deploy a server with a load balancer and public IP.
    It handles all steps sequentially, extracting IDs between steps.

    Args:
        ecs_name: Name for the ECS instance (required).
        elb_name: Name for the ELB load balancer (required).
        region: Huawei Cloud region.
        availability_zone: AZ. Auto-resolved if empty.
        flavor: ECS flavor, e.g. 's6.small.1'.
        image_id: Image ID. Auto-resolved per region if empty.
        vpc_id: VPC ID. Auto-resolved per region if empty.
        subnet_id: Subnet ID. Auto-resolved per region if empty.
        root_volume_type: Root disk type: 'SAS', 'SSD', 'GPSSD', 'ESSD'.
        root_volume_size: Root disk size in GB.
        elb_public_ip: True to create and bind a public EIP to the ELB.
        listener_protocol: Protocol for the listener (HTTP, HTTPS, TCP).
        listener_port: Port for the listener.
        pool_algorithm: LB algorithm (ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP).
        admin_pass: ECS admin password. Auto-generated if empty.
    """
    defaults = _resolve_defaults(region, vpc_id, subnet_id, image_id, availability_zone)
    resolved_vpc = defaults["vpc_id"]
    resolved_subnet = defaults["subnet_id"]
    resolved_image = defaults["image_id"]
    resolved_az = defaults["az"]

    if not resolved_image:
        resolved_image = "Ubuntu 22.04 server 64bit"
    if not admin_pass:
        admin_pass = f"Huawei@{int(time.time()) % 100000}!"

    summary = []
    errors = []

    # Step 1: Create ECS via CreatePostPaidServers
    logger.info("Full Stack Step 1/7: Creating ECS instance")
    server = {
        "name": ecs_name,
        "flavorRef": flavor,
        "availability_zone": resolved_az,
        "imageRef": resolved_image,
        "root_volume": {"volume_type": root_volume_type, "size": root_volume_size},
        "adminPass": admin_pass,
    }
    if resolved_vpc:
        server["vpcid"] = resolved_vpc
    if resolved_subnet:
        server["nics"] = [{"subnet_id": resolved_subnet}]

    ecs_result = execute_koocli("ECS", "CreatePostPaidServers", {"cli-region": region, "server": server})
    ecs_server_id = ""
    if "Error" not in ecs_result:
        ecs_server_id = _extract_id(ecs_result, [r'"id":\s*"([^"]+)"', r'"server_id":\s*"([^"]+)"'])

    if ecs_server_id:
        summary.append(f"ECS created: {ecs_name} (ID: {ecs_server_id})")
    else:
        errors.append(f"ECS creation failed: {ecs_result[:300]}")

    # Step 2: Get ECS private IP
    ecs_private_ip = ""
    if ecs_server_id:
        logger.info("Full Stack Step 2/7: Getting ECS private IP")
        time.sleep(8)
        detail = execute_koocli("ECS", "ShowServer", {
            "cli-region": region,
            "server_id": ecs_server_id,
        })
        all_ips = re.findall(r'"ip_address":\s*"(\d+\.\d+\.\d+\.\d+)"', detail)
        private_ips = [ip for ip in all_ips if not ip.startswith("100.") and ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.")]
        if private_ips:
            ecs_private_ip = private_ips[0]
        elif all_ips:
            ecs_private_ip = all_ips[0]
        if ecs_private_ip:
            summary.append(f"ECS private IP: {ecs_private_ip}")

    # Step 3: Create ELB (dedicated, no public_ip - we bind EIP separately)
    logger.info("Full Stack Step 3/7: Creating ELB load balancer")
    elb_name_safe = sanitize_params({"n": elb_name})["n"]
    lb = {
        "name": elb_name_safe,
        "guaranteed": "true",
        "availability_zone_list": [resolved_az],
    }
    if resolved_vpc:
        lb["vpc_id"] = resolved_vpc
    if resolved_subnet:
        lb["elb_virsubnet_ids"] = [resolved_subnet]

    elb_result = execute_koocli("ELB", "CreateLoadBalancer", {"cli-region": region, "loadbalancer": lb})
    elb_id = _extract_id(elb_result, [r'"id":\s*"([^"]+)"'])
    if elb_id:
        summary.append(f"ELB created: {elb_name_safe} (ID: {elb_id})")
    else:
        errors.append(f"ELB creation failed: {elb_result[:300]}")

    # Step 4: Create Listener
    listener_id = ""
    if elb_id:
        logger.info("Full Stack Step 4/7: Creating Listener")
        listener_result = execute_koocli("ELB", "CreateListener", {
            "cli-region": region,
            "listener": {
                "loadbalancer_id": elb_id,
                "protocol": listener_protocol,
                "protocol_port": listener_port,
                "name": f"{elb_name_safe}-listener",
            },
        })
        listener_id = _extract_id(listener_result, [r'"id":\s*"([^"]+)"'])
        if listener_id:
            summary.append(f"Listener: {elb_name_safe}-listener (port {listener_port})")
        else:
            errors.append(f"Listener creation failed: {listener_result[:300]}")

    # Step 5: Create Pool
    pool_id = ""
    if listener_id:
        logger.info("Full Stack Step 5/7: Creating Pool")
        pool_result = execute_koocli("ELB", "CreatePool", {
            "cli-region": region,
            "pool": {
                "listener_id": listener_id,
                "protocol": listener_protocol,
                "lb_algorithm": pool_algorithm,
                "name": f"{elb_name_safe}-pool",
            },
        })
        pool_id = _extract_id(pool_result, [r'"id":\s*"([^"]+)"'])
        if pool_id:
            summary.append(f"Pool: {elb_name_safe}-pool ({pool_algorithm})")
        else:
            errors.append(f"Pool creation failed: {pool_result[:300]}")

    # Step 6: Add ECS as Member
    if pool_id and ecs_private_ip:
        logger.info("Full Stack Step 6/7: Adding ECS as Member")
        member_result = execute_koocli("ELB", "BatchCreateMembers", {
            "cli-region": region,
            "pool_id": pool_id,
            "members": [{"address": ecs_private_ip, "protocol_port": listener_port}],
        })
        if '"id"' in member_result or "Success" in member_result:
            summary.append(f"Member: {ecs_private_ip}:{listener_port}")
        else:
            errors.append(f"Member creation failed: {member_result[:300]}")

    # Step 7: Create EIP and bind to ELB via AssociatePublicips
    elb_public_address = ""
    if elb_public_ip and elb_id:
        logger.info("Full Stack Step 7/7: Creating and binding EIP to ELB")
        eip_result = execute_koocli("EIP", "CreatePublicip", {
            "cli-region": region,
            "publicip": {"type": "5_bgp"},
            "bandwidth": {"name": f"{elb_name_safe}-bw", "size": 5, "charge_mode": "traffic"},
        })
        eip_id = _extract_id(eip_result, [r'"id":\s*"([^"]+)"'])

        if eip_id:
            summary.append(f"EIP created: {eip_id}")
            time.sleep(3)
            assoc_result = execute_koocli("EIP", "AssociatePublicips", {
                "cli-region": region,
                "publicip_id": eip_id,
                "publicip": {
                    "associate_instance_id": elb_id,
                    "associate_instance_type": "LOADBALANCER",
                },
            })
            if "Error" not in assoc_result:
                time.sleep(3)
                eip_detail = execute_koocli("EIP", "ShowPublicip", {
                    "cli-region": region,
                    "publicip_id": eip_id,
                })
                elb_public_address = _extract_id(eip_detail, [
                    r'"public_ip_address":\s*"([^"]+)"',
                    r'"ip_address":\s*"(\d+\.\d+\.\d+\.\d+)"',
                ])
                if elb_public_address:
                    summary.append(f"EIP bound to ELB: {elb_public_address}")
                else:
                    summary.append(f"EIP bound to ELB (ID: {eip_id})")
            else:
                errors.append(f"EIP association failed: {assoc_result[:300]}")
        else:
            errors.append(f"EIP creation failed: {eip_result[:300]}")

    result_parts = ["=== Full Stack Deployment ==="]
    result_parts.extend(summary)
    if errors:
        result_parts.append("\n--- Errors ---")
        result_parts.extend(errors)
    if elb_public_address:
        result_parts.append(f"\nELB Public IP: {elb_public_address}")
    result_parts.append(f"\nRegion: {region} | AZ: {resolved_az}")

    return "\n".join(result_parts)
