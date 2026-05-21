import json
import re
from typing import Any

from langchain_core.tools import tool

from tools.common.koocli_runner import run_cloud_command
from tools.registry import ToolMeta, ToolCategory
from cloud.result import CloudResult
from cloud.validation import validate_empty_result
from config.settings import get_settings
from config.logging import get_logger

logger = get_logger("tools.ims")

_PRIMARY_REGIONS = ["la-north-2", "ap-southeast-3", "ap-southeast-1", "cn-north-4"]


def _default_region(region: str) -> str:
    return region or get_settings().huawei_region


def _dump(result: CloudResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True)


def _extract_images(data: Any) -> list[dict]:
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in ("images", "image", "items"):
            items = data.get(k)
            if isinstance(items, list) and items:
                return [x for x in items if isinstance(x, dict)]
    return []


def _merge_images(service: str, operation: str, region: str | None, params: dict) -> CloudResult:
    if region:
        regions = [region]
    else:
        regions = _PRIMARY_REGIONS

    all_items = []
    total_elapsed = 0
    last_error = None
    found_data = False

    for r in regions:
        p = {**params, "cli-region": r}
        result = run_cloud_command(service, operation, p, use_cache=True)
        total_elapsed += result.elapsed_ms
        if result.ok and result.data:
            items = _extract_images(result.data)
            if items:
                found_data = True
                for item in items:
                    item["_region"] = r
                    all_items.append(item)
        elif not result.ok:
            last_error = result.error

    if found_data or all_items:
        return CloudResult.success("IMS", operation, {"images": all_items}, elapsed_ms=total_elapsed, item_count=len(all_items))

    if last_error:
        return CloudResult.from_error("IMS", operation, last_error, total_elapsed)

    return CloudResult.empty("IMS", operation, total_elapsed)


@tool
def list_images(region: str = "", image_type: str = "", name_filter: str = "") -> str:
    """List IMS images (private, public, shared, or market) in Huawei Cloud.
    Use this tool to find image IDs by name before deploying ECS instances.

    Args:
        region: Huawei Cloud region. Defaults to configured region.
        image_type: Image type filter: 'private', 'gold' (public), 'shared', or 'market'. Empty = all.
        name_filter: Partial name to filter images by (case-insensitive). Empty = list all.
    """
    params: dict[str, Any] = {}
    if image_type:
        params["__imagetype"] = image_type

    result = _merge_images("IMS", "ListImages", region or None, params)

    if result.ok and result.data and name_filter:
        images = _extract_images(result.data)
        pattern = re.compile(re.escape(name_filter), re.IGNORECASE)
        filtered = [img for img in images if pattern.search(img.get("name", ""))]
        result.data = {"images": filtered}
        result.item_count = len(filtered)

    if result.ok and result.data:
        images = _extract_images(result.data)
        for img in images:
            for key in list(img.keys()):
                if key.startswith("__") and key not in ("__imagetype", "__os_type", "__os_version", "__platform"):
                    del img[key]
        result.data = {"images": images}

    empty = validate_empty_result(result, "IMS", "ListImages")
    if empty:
        return json.dumps({"ok": True, "service": "IMS", "operation": "ListImages", "data": None, "item_count": 0, "message": empty})
    return _dump(result)


@tool
def find_image_id(name: str, region: str = "") -> str:
    """Find an IMS image ID by exact or partial name. Returns the image ID and details.
    Use this when you need to resolve an image name (like 'ims-web') to its UUID for ECS deployment.

    Args:
        name: Image name to search for (exact or partial match).
        region: Huawei Cloud region. Defaults to configured region.
    """
    region = _default_region(region)

    for img_type in ["private", "gold", "shared"]:
        params: dict[str, Any] = {"__imagetype": img_type, "cli-region": region}
        result = run_cloud_command("IMS", "ListImages", params, use_cache=True)
        if not result.ok or not result.data:
            continue
        images = _extract_images(result.data)
        for img in images:
            if img.get("name", "").lower() == name.lower():
                return json.dumps({
                    "ok": True,
                    "image_id": img["id"],
                    "name": img.get("name"),
                    "os_version": img.get("__os_version", ""),
                    "status": img.get("status"),
                    "region": region,
                    "image_type": img_type,
                })

    params = {"cli-region": region}
    result = run_cloud_command("IMS", "ListImages", params, use_cache=True)
    if result.ok and result.data:
        images = _extract_images(result.data)
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        for img in images:
            if pattern.search(img.get("name", "")):
                return json.dumps({
                    "ok": True,
                    "image_id": img["id"],
                    "name": img.get("name"),
                    "os_version": img.get("__os_version", ""),
                    "status": img.get("status"),
                    "region": region,
                    "image_type": img.get("__imagetype", ""),
                })

    return json.dumps({"ok": False, "error": f"Image '{name}' not found in region {region}"})


def resolve_image_name(image_ref: str, region: str) -> str:
    """Resolve an image name to its ID. If already a UUID, return as-is.
    If it looks like a name (not a UUID), search IMS for the matching image."""
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    if uuid_pattern.match(image_ref):
        return image_ref

    logger.info("Resolving image name '%s' in region %s", image_ref, region)
    for img_type in ["private", "gold", "shared"]:
        params: dict[str, Any] = {"__imagetype": img_type, "cli-region": region}
        result = run_cloud_command("IMS", "ListImages", params, use_cache=True)
        if not result.ok or not result.data:
            continue
        images = _extract_images(result.data)
        for img in images:
            if img.get("name", "").lower() == image_ref.lower():
                resolved_id = img["id"]
                logger.info("Resolved image '%s' -> %s (type=%s)", image_ref, resolved_id, img_type)
                return resolved_id

    params = {"cli-region": region}
    result = run_cloud_command("IMS", "ListImages", params, use_cache=True)
    if result.ok and result.data:
        images = _extract_images(result.data)
        pattern = re.compile(re.escape(image_ref), re.IGNORECASE)
        for img in images:
            if pattern.search(img.get("name", "")):
                resolved_id = img["id"]
                logger.info("Resolved image '%s' -> %s (partial match)", image_ref, resolved_id)
                return resolved_id

    logger.warning("Could not resolve image name '%s', returning as-is", image_ref)
    return image_ref


IMS_TOOLS: list[ToolMeta] = [
    ToolMeta(
        tool=list_images, service="IMS", category=ToolCategory.QUERY,
        keywords=["ims", "image", "images", "imagen", "imágenes", "ami", "snapshot"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
    ToolMeta(
        tool=find_image_id, service="IMS", category=ToolCategory.QUERY,
        keywords=["find image", "buscar imagen", "resolve image", "image id", "image name"],
        is_read_only=True, cacheable=True, cache_ttl=300,
    ),
]
