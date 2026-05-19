import json
import re
import shutil
import subprocess
import time
from typing import Optional

from langchain_core.tools import tool

from koocli.executor import execute_koocli, _find_hcloud_binary
from utils.sanitize import sanitize_params
from tools.registry import ToolMeta, ToolCategory
from cloud.validation import extract_id
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger("tools.deploy")
_settings = get_settings()

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
        "image_id": "b1eecdf6-a943-43f3-9d47-a538231d1442",
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


def _extract_private_ips(detail: str) -> list[str]:
    all_ips = re.findall(r'"ip_address":\s*"(\d+\.\d+\.\d+\.\d+)"', detail)
    if not all_ips:
        all_ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)', detail)
    private_ips = [ip for ip in all_ips if not ip.startswith("100.") and (ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."))]
    return private_ips, all_ips


@tool
def deploy_ecs_instance(
    name: str,
    region: str = "ap-southeast-3",
    availability_zone: str = "",
    flavor: str = "s6.small.1",
    image_id: str = "",
    vpc_id: str = "",
    subnet_id: str = "",
    security_group_id: str = "",
    root_volume_type: str = "SAS",
    root_volume_size: int = 40,
    admin_pass: str = "",
) -> str:
    """Deploys an ECS (Elastic Cloud Server) instance on Huawei Cloud.
    Use this tool INSTEAD of run_koocli_command for creating ECS instances.

    Args:
        name: Server name (required).
        region: Huawei Cloud region.
        availability_zone: AZ, e.g. 'ap-southeast-3a'. Auto-resolved if empty.
        flavor: Instance flavor, e.g. 's6.small.1', 's6.medium.2'.
        image_id: Image ID or name. Auto-resolved per region if empty.
        vpc_id: VPC ID. Auto-resolved per region if empty.
        subnet_id: Subnet ID. Auto-resolved per region if empty.
        security_group_id: Security Group ID to attach. Optional.
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
            "volumetype": root_volume_type,
            "size": root_volume_size,
        },
        "adminPass": admin_pass,
    }

    if resolved_vpc:
        server["vpcid"] = resolved_vpc
    if resolved_subnet:
        server["nics"] = [{"subnet_id": resolved_subnet}]
    if security_group_id:
        server["security_groups"] = [{"id": security_group_id}]

    params = {
        "cli-region": region,
        "server": server,
    }

    logger.info("Deploying ECS", extra={"structured_extra": {
        "name": name, "region": region, "flavor": flavor,
    }})

    result = execute_koocli("ECS", "CreatePostPaidServers", params)

    if "Error" in result:
        return f"ECS creation FAILED.\n{result}"

    server_id = extract_id(result, [
        r'"id":\s*"([^"]+)"',
        r'"server_id":\s*"([^"]+)"',
    ])

    if server_id:
        time.sleep(8)
        detail = execute_koocli("ECS", "ShowServer", {
            "cli-region": region,
            "server_id": server_id,
        })
        private_ips, all_ips = _extract_private_ips(detail)
        private_ip = private_ips[0] if private_ips else (all_ips[0] if all_ips else "")
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
def setup_elb_for_ecs(
    elb_name: str,
    ecs_server_ids: str = "",
    ecs_server_names: str = "",
    region: str = "la-north-2",
    availability_zone: str = "",
    vpc_id: str = "",
    subnet_id: str = "",
    listener_protocol: str = "HTTP",
    listener_port: int = 80,
    pool_algorithm: str = "ROUND_ROBIN",
    create_public_ip: bool = True,
    bandwidth_size: int = 5,
) -> str:
    """Sets up a complete ELB configuration for one or more EXISTING ECS instances in one call.
    Creates: ELB -> Listener -> Pool -> Members (all ECS) -> EIP (optional).
    Use this tool INSTEAD of calling multiple tools when the user wants to configure a load balancer for existing servers.
    Supports multiple ECS: pass comma-separated IDs in ecs_server_ids or comma-separated names in ecs_server_names.

    Args:
        elb_name: Name for the ELB load balancer (required).
        ecs_server_ids: Comma-separated ECS server IDs. If empty, resolves by ecs_server_names.
        ecs_server_names: Comma-separated ECS server names to search for if server_ids is empty.
        region: Huawei Cloud region (default la-north-2).
        availability_zone: AZ. Auto-resolved if empty.
        vpc_id: VPC ID. Auto-resolved per region if empty.
        subnet_id: Subnet ID. Auto-resolved per region if empty.
        listener_protocol: Protocol for the listener (HTTP, HTTPS, TCP).
        listener_port: Port for the listener (default 80).
        pool_algorithm: LB algorithm (ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP).
        create_public_ip: True to create and bind a public EIP to the ELB (default True).
        bandwidth_size: Bandwidth size in Mbit/s for the EIP (default 5).
    """
    defaults = _resolve_defaults(region, vpc_id, subnet_id, "", availability_zone)
    resolved_vpc = vpc_id or defaults["vpc_id"]
    resolved_subnet = subnet_id or defaults["subnet_id"]
    resolved_az = availability_zone or defaults["az"]

    summary = []
    errors = []

    if not ecs_server_ids and not ecs_server_names:
        return "Either ecs_server_ids or ecs_server_names must be provided."

    server_id_list = [s.strip() for s in ecs_server_ids.split(",") if s.strip()] if ecs_server_ids else []
    server_name_list = [s.strip() for s in ecs_server_names.split(",") if s.strip()] if ecs_server_names else []

    resolved_servers: list[dict] = []

    for sid in server_id_list:
        logger.info("ELB Setup: Resolving ECS by ID: %s", sid)
        detail = execute_koocli("ECS", "ShowServer", {
            "cli-region": region,
            "server_id": sid,
        })
        if "Error" in detail:
            errors.append(f"Could not get ECS details for {sid}: {detail[:200]}")
            continue
        name = extract_id(detail, [r'"name":\s*"([^"]+)"'])
        status = extract_id(detail, [r'"status":\s*"([^"]+)"'])
        private_ips, all_ips = _extract_private_ips(detail)
        private_ip = private_ips[0] if private_ips else (all_ips[0] if all_ips else "")
        resolved_servers.append({"id": sid, "name": name or sid, "ip": private_ip, "status": status})
        if not resolved_vpc:
            resolved_vpc = extract_id(detail, [r'"vpc_id":\s*"([^"]+)"'])
        if not resolved_subnet:
            subnet_matches = re.findall(r'"subnet_id":\s*"([^"]+)"', detail)
            if subnet_matches:
                resolved_subnet = subnet_matches[0]

    for sname in server_name_list:
        logger.info("ELB Setup: Resolving ECS by name: %s", sname)
        list_result = execute_koocli("ECS", "NovaListServers", {
            "cli-region": region,
        })
        all_ids = re.findall(r'"id":\s*"([^"]+)"', list_result)
        all_names = re.findall(r'"name":\s*"([^"]+)"', list_result)
        found_id = None
        for sid, sn in zip(all_ids, all_names):
            if sname.lower() in sn.lower():
                found_id = sid
                break
        if not found_id:
            errors.append(f"ECS server '{sname}' not found in region {region}. Available: {all_names[:10]}")
            continue

        detail = execute_koocli("ECS", "ShowServer", {
            "cli-region": region,
            "server_id": found_id,
        })
        if "Error" in detail:
            errors.append(f"Could not get ECS details for {found_id}: {detail[:200]}")
            continue
        name = extract_id(detail, [r'"name":\s*"([^"]+)"'])
        status = extract_id(detail, [r'"status":\s*"([^"]+)"'])
        private_ips, all_ips = _extract_private_ips(detail)
        private_ip = private_ips[0] if private_ips else (all_ips[0] if all_ips else "")
        resolved_servers.append({"id": found_id, "name": name or found_id, "ip": private_ip, "status": status})
        if not resolved_vpc:
            resolved_vpc = extract_id(detail, [r'"vpc_id":\s*"([^"]+)"'])
        if not resolved_subnet:
            subnet_matches = re.findall(r'"subnet_id":\s*"([^"]+)"', detail)
            if subnet_matches:
                resolved_subnet = subnet_matches[0]

    if not resolved_servers:
        return f"No ECS servers could be resolved. Errors:\n" + "\n".join(errors)

    for srv in resolved_servers:
        if srv["ip"]:
            summary.append(f"ECS: {srv['name']} | IP: {srv['ip']} | Status: {srv['status']}")
        else:
            errors.append(f"No private IP found for ECS {srv['name']} ({srv['id']})")

    logger.info("ELB Setup Step 2/6: Creating ELB load balancer")
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
    elb_id = extract_id(elb_result, [r'"id":\s*"([^"]+)"'])
    if elb_id:
        summary.append(f"ELB created: {elb_name_safe} (ID: {elb_id})")
    else:
        errors.append(f"ELB creation failed: {elb_result[:300]}")
        result_parts = ["=== ELB Setup for ECS - FAILED ==="] + summary
        if errors:
            result_parts.append("\n--- Errors ---")
            result_parts.extend(errors)
        return "\n".join(result_parts)

    listener_id = ""
    logger.info("ELB Setup Step 3/6: Creating Listener")
    time.sleep(2)
    listener_result = execute_koocli("ELB", "CreateListener", {
        "cli-region": region,
        "listener": {
            "loadbalancer_id": elb_id,
            "protocol": listener_protocol,
            "protocol_port": listener_port,
            "name": f"{elb_name_safe}-listener",
        },
    })
    listener_id = extract_id(listener_result, [r'"id":\s*"([^"]+)"'])
    if listener_id:
        summary.append(f"Listener: {elb_name_safe}-listener (port {listener_port})")
    else:
        errors.append(f"Listener creation failed: {listener_result[:300]}")

    pool_id = ""
    if listener_id:
        logger.info("ELB Setup Step 4/6: Creating Pool")
        time.sleep(2)
        pool_result = execute_koocli("ELB", "CreatePool", {
            "cli-region": region,
            "pool": {
                "listener_id": listener_id,
                "protocol": listener_protocol,
                "lb_algorithm": pool_algorithm,
                "name": f"{elb_name_safe}-pool",
            },
        })
        pool_id = extract_id(pool_result, [r'"id":\s*"([^"]+)"'])
        if pool_id:
            summary.append(f"Pool: {elb_name_safe}-pool ({pool_algorithm})")
        else:
            errors.append(f"Pool creation failed: {pool_result[:300]}")

    if pool_id:
        members_with_ip = [srv for srv in resolved_servers if srv["ip"]]
        if members_with_ip:
            logger.info("ELB Setup Step 5/6: Adding %d ECS members to pool", len(members_with_ip))
            time.sleep(2)
            members_payload = [
                {"address": srv["ip"], "protocol_port": listener_port}
                for srv in members_with_ip
            ]
            member_result = execute_koocli("ELB", "BatchCreateMembers", {
                "cli-region": region,
                "pool_id": pool_id,
                "members": members_payload,
            })
            if '"id"' in member_result or "Success" in member_result:
                member_summary = ", ".join(f"{srv['ip']}:{listener_port}" for srv in members_with_ip)
                summary.append(f"Members ({len(members_with_ip)}): {member_summary}")
            else:
                errors.append(f"Member creation failed: {member_result[:300]}")
        else:
            errors.append("Step 5 SKIPPED: no ECS private IPs available to add as members")
            logger.warning("Step 5 skipped: no private IPs, pool_id=%s", pool_id)

    elb_public_address = ""
    if create_public_ip and elb_id:
        logger.info("ELB Setup Step 6/6: Creating and binding EIP to ELB")
        time.sleep(2)
        eip_result = execute_koocli("EIP", "CreatePublicip", {
            "cli-region": region,
            "publicip": {"type": "5_bgp"},
            "bandwidth": {"name": f"{elb_name_safe}-bw", "size": bandwidth_size, "charge_mode": "traffic", "share_type": "PER"},
        })
        eip_id = extract_id(eip_result, [r'"id":\s*"([^"]+)"'])

        if eip_id:
            summary.append(f"EIP created: {eip_id}")
            time.sleep(3)
            assoc_result = execute_koocli("EIP", "AssociatePublicips", {
                "cli-region": region,
                "publicip_id": eip_id,
                "publicip": {
                    "associate_instance_id": elb_id,
                    "associate_instance_type": "ELB",
                },
            })
            if "Error" not in assoc_result and "USE_ERROR" not in assoc_result:
                time.sleep(3)
                eip_detail = execute_koocli("EIP", "ShowPublicip", {
                    "cli-region": region,
                    "publicip_id": eip_id,
                })
                elb_public_address = extract_id(eip_detail, [
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

    result_parts = ["=== ELB Setup for ECS - COMPLETE ==="]
    result_parts.extend(summary)
    if errors:
        result_parts.append("\n--- Errors ---")
        result_parts.extend(errors)
    if elb_public_address:
        result_parts.append(f"\nELB Public IP: {elb_public_address}")
    result_parts.append(f"\nRegion: {region} | AZ: {resolved_az}")
    if not errors:
        result_parts.append("\n[ALL STEPS DONE. Do NOT call additional tools to repeat these steps.]")

    return "\n".join(result_parts)


@tool
def manage_ecs(
    action: str,
    server_id: str = "",
    server_name: str = "",
    region: str = "ap-southeast-3",
) -> str:
    """Manages ECS instances: start, stop, reboot, or get status.
    Use this tool INSTEAD of run_koocli_command for common ECS operations.

    Args:
        action: Operation to perform: 'start', 'stop', 'reboot', 'status'.
        server_id: Server ID. If empty, searches by server_name.
        server_name: Server name to search for if server_id is empty.
        region: Huawei Cloud region.
    """
    action = action.lower().strip()

    if not server_id and server_name:
        list_result = execute_koocli("ECS", "NovaListServers", {
            "cli-region": region,
            "name": server_name,
        })
        server_id = extract_id(list_result, [r'"id":\s*"([^"]+)"'])
        if not server_id:
            all_ids = re.findall(r'"id":\s*"([^"]+)"', list_result)
            all_names = re.findall(r'"name":\s*"([^"]+)"', list_result)
            for sid, sname in zip(all_ids, all_names):
                if server_name.lower() in sname.lower():
                    server_id = sid
                    break
        if not server_id:
            return f"Server '{server_name}' not found in region {region}."

    if not server_id:
        return "Either server_id or server_name must be provided."

    if action == "status":
        result = execute_koocli("ECS", "ShowServer", {
            "cli-region": region,
            "server_id": server_id,
        })
        status = extract_id(result, [r'"status":\s*"([^"]+)"'])
        private_ip = extract_id(result, [r'"ip_address":\s*"(\d+\.\d+\.\d+\.\d+)"'])
        name = extract_id(result, [r'"name":\s*"([^"]+)"'])
        return (
            f"ECS Status: {status}\n"
            f"Name: {name} | ID: {server_id}\n"
            f"Private IP: {private_ip}\n"
            f"Region: {region}"
        )

    op_map = {
        "start": "BatchStartServers",
        "stop": "BatchStopServers",
        "reboot": "BatchRebootServers",
    }
    op = op_map.get(action)
    if not op:
        return f"Unknown action '{action}'. Use: start, stop, reboot, status."

    key = "os-start" if action == "start" else "os-stop" if action == "stop" else "reboot"
    params = {
        "cli-region": region,
        key: {"servers": [{"id": server_id}]},
    }

    logger.info("Managing ECS: %s %s", action, server_id)
    result = execute_koocli("ECS", op, params)

    if "Error" in result:
        return f"ECS {action} FAILED for {server_id}.\n{result}"

    return f"ECS {action} command sent for server {server_id} in {region}."


@tool
def manage_eip(
    action: str,
    resource_id: str = "",
    resource_type: str = "ECS",
    region: str = "ap-southeast-3",
    eip_id: str = "",
) -> str:
    """Manages Elastic IPs: create, associate to ECS/ELB, or show status.
    Use this tool INSTEAD of run_koocli_command for EIP operations.

    Args:
        action: Operation: 'create', 'associate', 'show', 'delete'.
        resource_id: Server ID or ELB ID to associate the EIP to.
        resource_type: Type of resource: 'ECS' or 'ELB' (for associate action).
        region: Huawei Cloud region.
        eip_id: EIP ID (required for associate/show/delete).
    """
    action = action.lower().strip()

    if action == "create":
        result = execute_koocli("EIP", "CreatePublicip", {
            "cli-region": region,
            "publicip": {"type": "5_bgp"},
            "bandwidth": {"name": f"eip-bw-{int(time.time()) % 100000}", "size": 5, "charge_mode": "traffic", "share_type": "PER"},
        })
        if "Error" in result:
            return f"EIP creation FAILED.\n{result}"
        new_eip_id = extract_id(result, [r'"id":\s*"([^"]+)"'])
        public_ip = extract_id(result, [r'"public_ip_address":\s*"([^"]+)"'])
        return (
            f"EIP created SUCCESSFULLY.\n"
            f"EIP ID: {new_eip_id}\n"
            f"Public IP: {public_ip}\n"
            f"Region: {region}"
        )

    if action == "associate":
        if not eip_id or not resource_id:
            return "Both eip_id and resource_id are required for associate action."

        if resource_type.upper() == "ELB":
            assoc_result = execute_koocli("EIP", "AssociatePublicips", {
                "cli-region": region,
                "publicip_id": eip_id,
                "publicip": {
                    "associate_instance_id": resource_id,
                    "associate_instance_type": "ELB",
                },
            })
        else:
            detail = execute_koocli("ECS", "ShowServer", {
                "cli-region": region,
                "server_id": resource_id,
            })
            port_id = extract_id(detail, [r'"port_id":\s*"([^"]+)"'])
            if not port_id:
                all_ports = re.findall(r'"port_id":\s*"([^"]+)"', detail)
                port_id = all_ports[0] if all_ports else ""
            if not port_id:
                return f"Could not find port_id for server {resource_id}."
            assoc_result = execute_koocli("EIP", "UpdatePublicip", {
                "cli-region": region,
                "publicip_id": eip_id,
                "publicip": {"port_id": port_id},
            })

        if "Error" in assoc_result:
            return f"EIP association FAILED.\n{assoc_result}"
        return f"EIP {eip_id} associated to {resource_type} {resource_id} in {region}."

    if action == "show":
        if not eip_id:
            return "eip_id is required for show action."
        result = execute_koocli("EIP", "ShowPublicip", {
            "cli-region": region,
            "publicip_id": eip_id,
        })
        return result

    if action == "delete":
        if not eip_id:
            return "eip_id is required for delete action."
        result = execute_koocli("EIP", "DeletePublicip", {
            "cli-region": region,
            "publicip_id": eip_id,
        })
        return result

    return f"Unknown action '{action}'. Use: create, associate, show, delete."


@tool
def deploy_obs_bucket(
    bucket_name: str,
    region: str = "la-north-2",
    storage_class: str = "standard",
    acl: str = "private",
) -> str:
    """Creates an OBS (Object Storage Service) bucket on Huawei Cloud using hcloud obs.
    Use this tool to create OBS buckets for storing static files, assets, or data.

    Args:
        bucket_name: Globally unique bucket name (required).
        region: Huawei Cloud region (default la-north-2).
        storage_class: Storage class: standard, warm, cold, deep-archive (default standard).
        acl: Access control: private, public-read, public-read-write (default private).
    """
    hcloud_path = _find_hcloud_binary()
    if not hcloud_path:
        return "Error: 'hcloud' is not installed. Install KooCLI and ensure it is in PATH."

    ak = _settings.huawei_ak
    sk = _settings.huawei_sk
    if not ak or not sk:
        return "Error: Missing HUAWEI_AK or HUAWEI_SK in .env"

    cmd = (
        f'"{hcloud_path}" obs mb obs://{bucket_name}'
        f' -location={region}'
        f' -sc={storage_class}'
        f' -acl={acl}'
        f' -i={ak}'
        f' -k={sk}'
    )

    logger.info("Creating OBS bucket: %s in %s", bucket_name, region)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False,
            shell=True, timeout=60,
        )
        combined = (result.stdout or "") + (result.stderr or "")

        if "successfully" in combined.lower() or "successfully" in combined:
            logger.info("OBS bucket created: %s", bucket_name)
            return (
                f"OBS bucket '{bucket_name}' created SUCCESSFULLY.\n"
                f"Region: {region} | Storage: {storage_class} | ACL: {acl}"
            )

        if "already exists" in combined.lower() or "AlreadyExists" in combined:
            return (
                f"OBS bucket '{bucket_name}' already exists.\n"
                f"Region: {region} | Storage: {storage_class} | ACL: {acl}"
            )

        logger.warning("OBS bucket creation failed: %s", combined[:300])
        return f"OBS bucket creation FAILED for '{bucket_name}'.\n{combined[:500]}"

    except subprocess.TimeoutExpired:
        return f"Error: OBS bucket creation timed out after 60s."
    except Exception as exc:
        return f"Error creating OBS bucket: {str(exc)}"


DEPLOY_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=deploy_obs_bucket, service="DEPLOY", category=ToolCategory.DEPLOY,
        keywords=["create obs", "deploy obs", "obs bucket", "crear obs", "bucket obs", "almacenamiento objeto", "object storage"],
        is_read_only=False, cacheable=False,
    ),
    ToolMeta(
        tool=deploy_ecs_instance, service="DEPLOY", category=ToolCategory.DEPLOY,
        keywords=["deploy ecs", "create ecs", "crear ecs", "create server", "desplegar ecs"],
        is_read_only=False, cacheable=False,
    ),
    ToolMeta(
        tool=setup_elb_for_ecs, service="DEPLOY", category=ToolCategory.DEPLOY,
        keywords=["setup elb", "configure elb", "configurar elb", "elb for ecs", "load balancer for", "asociar elb", "crear elb para"],
        is_read_only=False, cacheable=False,
    ),
    ToolMeta(
        tool=manage_ecs, service="DEPLOY", category=ToolCategory.MANAGE,
        keywords=["manage ecs", "start ecs", "stop ecs", "reboot ecs", "ecs status"],
        is_read_only=False, cacheable=False,
    ),
    ToolMeta(
        tool=manage_eip, service="DEPLOY", category=ToolCategory.MANAGE,
        keywords=["manage eip", "associate eip", "create eip", "release eip"],
        is_read_only=False, cacheable=False,
    ),
]
