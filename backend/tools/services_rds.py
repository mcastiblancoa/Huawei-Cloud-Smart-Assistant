import json
import re
import time
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_cloud_command
from tools.common.table_formatter import format_table, RDS_COLUMNS
from tools.registry import ToolMeta, ToolCategory
from cloud.result import CloudResult
from cloud.validation import validate_empty_result, extract_id
from config.settings import get_settings
from config.logging import get_logger

logger = get_logger("tools.rds")

_PRIMARY_REGIONS = ["la-north-2", "ap-southeast-3", "ap-southeast-1"]


def _default_region(region: str) -> str:
    return region or get_settings().huawei_region


def _dump(result: CloudResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True)


def _extract_list(data: Any, key: str) -> list[dict]:
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in (key, "instances", "dataStores", "flavors", "items"):
            items = data.get(k)
            if isinstance(items, list) and items:
                return [x for x in items if isinstance(x, dict)]
    return []


def _merge_list(service: str, operation: str, region: str | None, key: str, extra_params: dict | None = None) -> CloudResult:
    if region:
        regions = [region]
    else:
        regions = _PRIMARY_REGIONS

    all_items = []
    total_elapsed = 0
    last_error = None
    found_data = False

    for r in regions:
        params = {"cli-region": r}
        if extra_params:
            params.update(extra_params)
        result = run_cloud_command(service, operation, params, use_cache=True)
        total_elapsed += result.elapsed_ms
        if result.ok and result.data:
            items = _extract_list(result.data, key)
            if items:
                found_data = True
                for item in items:
                    item["_region"] = r
                    all_items.append(item)
        elif not result.ok:
            last_error = result.error

    if found_data or all_items:
        merged = {key: all_items} if key else all_items
        return CloudResult.success(service, operation, merged, elapsed_ms=total_elapsed, item_count=len(all_items))

    if last_error:
        return CloudResult.from_error(service, operation, last_error, total_elapsed)

    return CloudResult.empty(service, operation, total_elapsed)


@tool
def list_rds(region: str = "") -> str:
    """List all RDS (Relational Database Service) instances across regions.
    Returns real data from Huawei Cloud."""
    result = _merge_list("RDS", "ListInstances", region or None, "instances")
    if result.ok and result.data:
        instances = _extract_list(result.data, "instances")
        for inst in instances:
            for k in list(inst.keys()):
                if k.startswith("_") and k != "_region":
                    del inst[k]
        result.data = {"instances": instances}
        result.item_count = len(instances)
    empty = validate_empty_result(result, "RDS", "ListInstances")
    if empty:
        return json.dumps({"ok": True, "service": "RDS", "operation": "ListInstances", "data": None, "item_count": 0, "message": empty})
    table_md = format_table(instances, RDS_COLUMNS)
    d = result.to_dict()
    if table_md:
        d["_table"] = table_md
    return json.dumps(d, ensure_ascii=True)


@tool
def list_rds_datastores(engine: str = "MySQL", region: str = "") -> str:
    """List available RDS database engine versions (datastores).
    Use this to find valid engine versions before creating an RDS instance.

    Args:
        engine: DB engine type: 'MySQL', 'PostgreSQL', 'SQLServer', or 'MariaDB'.
        region: Huawei Cloud region.
    """
    region = _default_region(region)
    params = {"database_name": engine, "cli-region": region}
    result = run_cloud_command("RDS", "ListDatastores", params, use_cache=True)
    if not result.ok:
        return json.dumps({"ok": False, "service": "RDS", "error": result.error})
    return _dump(result)


@tool
def list_rds_flavors(engine: str = "MySQL", version: str = "8.0", region: str = "") -> str:
    """List available RDS flavor specifications (CPU/memory combos) for a given engine and version.
    Use this to find valid flavor_ref values before creating an RDS instance.

    Args:
        engine: DB engine type: 'MySQL', 'PostgreSQL', 'SQLServer', or 'MariaDB'.
        version: DB engine version, e.g. '8.0', '5.7'.
        region: Huawei Cloud region.
    """
    region = _default_region(region)
    params = {"database_name": engine, "version_name": version, "cli-region": region}
    result = run_cloud_command("RDS", "ListFlavors", params, use_cache=True)
    if not result.ok:
        return json.dumps({"ok": False, "service": "RDS", "error": result.error})

    if result.ok and result.data:
        flavors = _extract_list(result.data, "flavors")
        simplified = []
        for f in flavors:
            az_status = f.get("az_status", {})
            available_azs = [az for az, status in az_status.items() if status == "normal"]
            mode = f.get("instance_mode", "")
            simplified.append({
                "spec_code": f.get("spec_code", ""),
                "vcpus": f.get("vcpus", ""),
                "ram": f.get("ram", ""),
                "instance_mode": mode,
                "available_azs": available_azs,
            })
        result.data = {"flavors": simplified}
        result.item_count = len(simplified)

    return _dump(result)


@tool
def list_rds_storage_types(engine: str = "MySQL", version: str = "8.0", region: str = "") -> str:
    """List available storage types for RDS instances.

    Args:
        engine: DB engine type.
        version: DB engine version.
        region: Huawei Cloud region.
    """
    region = _default_region(region)
    params = {"database_name": engine, "version_name": version, "cli-region": region}
    result = run_cloud_command("RDS", "ListStorageTypes", params, use_cache=True)
    if not result.ok:
        return json.dumps({"ok": False, "service": "RDS", "error": result.error})
    return _dump(result)


@tool
def create_rds_instance(
    name: str,
    engine: str = "MySQL",
    engine_version: str = "8.0",
    flavor_ref: str = "rds.mysql.n1.large.2",
    volume_type: str = "CLOUDSSD",
    volume_size: int = 40,
    region: str = "la-north-2",
    availability_zone: str = "",
    vpc_id: str = "",
    subnet_id: str = "",
    security_group_id: str = "",
    password: str = "",
    ha_mode: str = "",
    port: int = 0,
) -> str:
    """Create an RDS (Relational Database Service) instance on Huawei Cloud.
    Use this tool INSTEAD of run_koocli_command for creating RDS instances.

    Args:
        name: DB instance name (4-64 chars, starts with letter, letters/digits/hyphens/underscores).
        engine: DB engine: 'MySQL', 'PostgreSQL', 'SQLServer', or 'MariaDB'.
        engine_version: Engine version, e.g. '8.0', '5.7' for MySQL.
        flavor_ref: Flavor spec code, e.g. 'rds.mysql.n1.large.2' (2 vCPU, 4GB). Use list_rds_flavors to find valid values.
        volume_type: Volume type: 'ULTRAHIGH' (SSD), 'HIGH' (SAS), 'COMMON' (SATA), 'GPSSD2', 'CLOUDSSD', 'LOCALSSD', 'ESSD'.
        volume_size: Volume size in GB (multiple of 10, 40-4000).
        region: Huawei Cloud region.
        availability_zone: AZ, e.g. 'la-north-2a'. Auto-resolved if empty.
        vpc_id: VPC ID. Auto-resolved if empty.
        subnet_id: Subnet ID. Auto-resolved if empty.
        security_group_id: Security Group ID. Auto-resolved if empty.
        password: Database root password. Auto-generated if empty.
        ha_mode: HA mode: 'Ha' for primary/standby, '' for single node.
        port: Database port. Default: 3306 (MySQL), 5432 (PostgreSQL), 1433 (SQLServer).
    """
    _settings = get_settings()

    REGION_DEFAULTS = {
        "la-north-2": {
            "vpc_id": "dfbefb5b-d128-47a1-b0d2-2b5b9b0ecb1b",
            "subnet_id": "3b5b940f-a55f-4bc1-bcb0-f3e5be7d70df",
            "az": "la-north-2a",
        },
        "ap-southeast-3": {
            "vpc_id": "28ea9627-edb0-4b94-a6eb-051d0dcfabcf",
            "subnet_id": "10e9345f-63c6-4d99-a0c7-a75ecb88d0f3",
            "az": "ap-southeast-3a",
        },
    }

    defaults = REGION_DEFAULTS.get(region, {})
    resolved_vpc = vpc_id or defaults.get("vpc_id", "")
    resolved_subnet = subnet_id or defaults.get("subnet_id", "")
    resolved_az = availability_zone or defaults.get("az", "")

    if not resolved_vpc or not resolved_subnet:
        return json.dumps({"ok": False, "error": f"VPC and Subnet are required for region {region}. Provide vpc_id and subnet_id."})

    if not resolved_az:
        return json.dumps({"ok": False, "error": f"Availability zone is required for region {region}. Provide availability_zone."})

    if not security_group_id:
        sg_result = run_cloud_command("VPC", "ListSecurityGroups", {"cli-region": region, "vpc_id": resolved_vpc}, use_cache=True)
        if sg_result.ok and sg_result.data:
            sgs = _extract_list(sg_result.data, "security_groups")
            for sg in sgs:
                if "default" in sg.get("name", "").lower() or sg.get("name", "") == "default":
                    security_group_id = sg.get("id", "")
                    logger.info("Auto-resolved security group: %s (%s)", sg.get("name"), security_group_id)
                    break
            if not security_group_id and sgs:
                security_group_id = sgs[0].get("id", "")
                logger.info("Using first security group: %s (%s)", sgs[0].get("name"), security_group_id)

    if not password:
        password = f"Rds@{int(time.time()) % 100000}!Aa1"

    project_id = _settings.huawei_project_id
    if not project_id:
        return json.dumps({"ok": False, "error": "HUAWEI_PROJECT_ID not configured. Set it in .env."})

    params: dict[str, Any] = {
        "name": name,
        "region": region,
        "availability_zone": resolved_az,
        "project_id": project_id,
        "datastore.type": engine,
        "datastore.version": engine_version,
        "flavor_ref": flavor_ref,
        "volume.type": volume_type,
        "volume.size": volume_size,
        "vpc_id": resolved_vpc,
        "subnet_id": resolved_subnet,
        "security_group_id": security_group_id,
        "password": password,
        "cli-region": region,
    }

    if ha_mode:
        params["ha.mode"] = ha_mode
        if ha_mode.lower() == "ha":
            params["ha.replication_mode"] = "async"
            if "," not in resolved_az:
                secondary_az = resolved_az[:-1] + "b" if resolved_az.endswith("a") else resolved_az
                params["availability_zone"] = f"{resolved_az},{secondary_az}"

    if port:
        params["port"] = str(port)

    logger.info("Creating RDS instance '%s' (%s %s, %s, %dGB) in %s", name, engine, engine_version, flavor_ref, volume_size, region)

    result = run_cloud_command("RDS", "CreateInstance", params, use_cache=False)

    if not result.ok:
        return json.dumps({"ok": False, "service": "RDS", "operation": "CreateInstance", "error": result.error})

    instance_id = ""
    if result.data:
        if isinstance(result.data, dict):
            instance = result.data.get("instance", result.data)
            instance_id = instance.get("id", "")

    if instance_id:
        logger.info("RDS instance created: %s (%s)", name, instance_id)
        job_done = _wait_for_rds_job(instance_id, region)
        if job_done:
            show_result = run_cloud_command("RDS", "ShowInstanceConfiguration", {"instance_id": instance_id, "cli-region": region}, use_cache=False)
            if show_result.ok:
                return json.dumps({
                    "ok": True,
                    "service": "RDS",
                    "operation": "CreateInstance",
                    "instance_id": instance_id,
                    "name": name,
                    "engine": engine,
                    "engine_version": engine_version,
                    "flavor_ref": flavor_ref,
                    "volume_type": volume_type,
                    "volume_size": volume_size,
                    "region": region,
                    "az": resolved_az,
                    "status": "created",
                })

    return json.dumps({
        "ok": True,
        "service": "RDS",
        "operation": "CreateInstance",
        "instance_id": instance_id,
        "name": name,
        "engine": engine,
        "engine_version": engine_version,
        "region": region,
        "status": "creating",
    })


def _wait_for_rds_job(instance_id: str, region: str, timeout: int = 180, interval: int = 15) -> bool:
    """Wait for RDS instance to become available by polling."""
    elapsed = 0
    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
        result = run_cloud_command("RDS", "ListInstances", {"cli-region": region}, use_cache=False)
        if result.ok and result.data:
            instances = _extract_list(result.data, "instances")
            for inst in instances:
                if inst.get("id") == instance_id:
                    status = inst.get("status", "")
                    if status == "ACTIVE":
                        logger.info("RDS instance %s is ACTIVE after %ds", instance_id, elapsed)
                        return True
                    if status in ("FAILED", "abnormal"):
                        logger.warning("RDS instance %s failed: %s", instance_id, status)
                        return False
        logger.debug("Waiting for RDS instance %s... (%ds)", instance_id, elapsed)
    logger.warning("Timeout waiting for RDS instance %s after %ds", instance_id, timeout)
    return False


@tool
def delete_rds_instance(instance_id: str, region: str = "la-north-2") -> str:
    """Delete an RDS instance by instance_id.

    Args:
        instance_id: RDS instance ID to delete.
        region: Huawei Cloud region.
    """
    project_id = get_settings().huawei_project_id
    params = {"instance_id": instance_id, "cli-region": region}
    if project_id:
        params["project_id"] = project_id

    logger.info("Deleting RDS instance %s in %s", instance_id, region)
    result = run_cloud_command("RDS", "DeleteInstance", params, use_cache=False)

    if not result.ok:
        if "not supported" in (result.error or "") or "DBS.200018" in (result.error or ""):
            return json.dumps({"ok": False, "service": "RDS", "operation": "DeleteInstance", "instance_id": instance_id, "error": "Instance is still being created. Wait until status is ACTIVE before deleting.", "region": region})
        return json.dumps({"ok": False, "service": "RDS", "operation": "DeleteInstance", "error": result.error})

    return json.dumps({"ok": True, "service": "RDS", "operation": "DeleteInstance", "instance_id": instance_id, "region": region, "status": "deleting"})


@tool
def list_rds_backups(instance_id: str = "", region: str = "") -> str:
    """List RDS backups. Optionally filter by instance_id.

    Args:
        instance_id: RDS instance ID to filter backups. Empty = list all.
        region: Huawei Cloud region.
    """
    region = _default_region(region)
    params: dict[str, Any] = {"cli-region": region}
    if instance_id:
        params["instance_id"] = instance_id

    result = run_cloud_command("RDS", "ListBackups", params, use_cache=True)
    if not result.ok:
        return json.dumps({"ok": False, "service": "RDS", "error": result.error})
    return _dump(result)


@tool
def list_rds_error_logs(instance_id: str, region: str = "") -> str:
    """List error logs for an RDS instance.

    Args:
        instance_id: RDS instance ID.
        region: Huawei Cloud region.
    """
    region = _default_region(region)
    params = {"instance_id": instance_id, "cli-region": region}
    result = run_cloud_command("RDS", "ListErrorLogsNew", params, use_cache=True)
    if not result.ok:
        result = run_cloud_command("RDS", "ListErrorLogs", params, use_cache=True)
    if not result.ok:
        return json.dumps({"ok": False, "service": "RDS", "error": result.error})
    return _dump(result)


@tool
def list_rds_slow_logs(instance_id: str, region: str = "") -> str:
    """List slow query logs for an RDS instance.

    Args:
        instance_id: RDS instance ID.
        region: Huawei Cloud region.
    """
    region = _default_region(region)
    params = {"instance_id": instance_id, "cli-region": region}
    result = run_cloud_command("RDS", "ListSlowLogsNew", params, use_cache=True)
    if not result.ok:
        result = run_cloud_command("RDS", "ListSlowLogs", params, use_cache=True)
    if not result.ok:
        return json.dumps({"ok": False, "service": "RDS", "error": result.error})
    return _dump(result)


RDS_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_rds, service="RDS", category=ToolCategory.QUERY,
        keywords=["rds", "database", "db", "mysql", "postgres", "sqlserver", "mariadb", "base de datos", "instancia rds"],
        is_read_only=True, cacheable=True, cache_ttl=30,
    ),
    ToolMeta(
        tool=list_rds_datastores, service="RDS", category=ToolCategory.QUERY,
        keywords=["rds versions", "rds engines", "datastore", "motor rds", "version mysql"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
    ToolMeta(
        tool=list_rds_flavors, service="RDS", category=ToolCategory.QUERY,
        keywords=["rds flavors", "rds specs", "rds sizes", "flavor rds", "especificaciones rds"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
    ToolMeta(
        tool=list_rds_storage_types, service="RDS", category=ToolCategory.QUERY,
        keywords=["rds storage", "storage type rds", "tipo almacenamiento rds"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
    ToolMeta(
        tool=create_rds_instance, service="RDS", category=ToolCategory.DEPLOY,
        keywords=["create rds", "crear rds", "create database", "crear base de datos", "deploy rds", "desplegar rds"],
        is_read_only=False, is_destructive=False, cacheable=False,
    ),
    ToolMeta(
        tool=delete_rds_instance, service="RDS", category=ToolCategory.DELETE,
        keywords=["delete rds", "eliminar rds", "borrar rds", "delete database", "eliminar base de datos"],
        is_read_only=False, is_destructive=True, cacheable=False,
    ),
    ToolMeta(
        tool=list_rds_backups, service="RDS", category=ToolCategory.QUERY,
        keywords=["rds backups", "backups rds", "respaldos rds"],
        is_read_only=True, cacheable=True, cache_ttl=30,
    ),
    ToolMeta(
        tool=list_rds_error_logs, service="RDS", category=ToolCategory.QUERY,
        keywords=["rds error logs", "error logs rds", "logs error rds"],
        is_read_only=True, cacheable=True, cache_ttl=15,
    ),
    ToolMeta(
        tool=list_rds_slow_logs, service="RDS", category=ToolCategory.QUERY,
        keywords=["rds slow logs", "slow queries rds", "consultas lentas rds"],
        is_read_only=True, cacheable=True, cache_ttl=15,
    ),
]
