import shutil
import subprocess
from pathlib import Path
from typing import Any

from config.logging import get_logger
from config.settings import get_settings
from koocli.params import build_cli_args, AUTO_INJECTED_PARAMS
from koocli.regions import resolve_region, resolve_project_id, needs_domain_id
from utils.retry import retry_with_backoff

logger = get_logger("koocli.executor")

_settings = get_settings()


def _find_hcloud_binary() -> str | None:
    path = shutil.which("hcloud")
    if path:
        return path
    workspace = _settings.root_dir
    candidates = [
        workspace / "bin" / "hcloud.exe",
        workspace / "hcloud.exe",
        Path.home() / "Downloads" / "huaweicloud-cli-windows-amd64" / "hcloud.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _build_full_command(
    service: str,
    operation: str,
    params: dict[str, Any] | None,
) -> list[str]:
    ak = _settings.huawei_ak
    sk = _settings.huawei_sk
    region = resolve_region(service, _settings.huawei_region)
    project_id = resolve_project_id(region, _settings.huawei_project_id)
    domain_id = _settings.cloud_sdk_domain_id if needs_domain_id(service) else None

    cmd_parts, resolved_region = build_cli_args(
        service, operation, params, ak, sk, region, project_id, domain_id,
    )

    actual_project_id = resolve_project_id(resolved_region, _settings.huawei_project_id)
    if actual_project_id and params and "project_id" not in params:
        cmd_parts.append(f"--project_id={actual_project_id}")

    if domain_id:
        cmd_parts.append(f"--domain_id={domain_id}")

    return cmd_parts


def execute_koocli(
    service: str,
    operation: str,
    params: dict[str, Any] | None = None,
) -> str:
    hcloud_path = _find_hcloud_binary()
    if not hcloud_path:
        return "Error: 'hcloud' is not installed. Install KooCLI and ensure it is in PATH."

    if not _settings.huawei_ak or not _settings.huawei_sk or not _settings.huawei_region:
        return "Error: Missing credentials (HUAWEI_AK, HUAWEI_SK, HUAWEI_REGION) in .env"

    cmd_parts = _build_full_command(service, operation, params)
    cmd_str = f'"{hcloud_path}" {" ".join(cmd_parts)}'

    logger.info(
        "Executing KooCLI command",
        extra={"structured_extra": {
            "service": service,
            "operation": operation,
            "has_params": params is not None,
        }},
    )

    try:
        result = subprocess.run(
            cmd_str,
            capture_output=True,
            text=True,
            check=False,
            shell=True,
            timeout=_settings.koocli_timeout,
        )

        output = result.stdout if result.returncode == 0 else result.stderr
        max_length = _settings.koocli_max_output

        if len(output) > max_length:
            output = output[:max_length] + (
                f"\n\n...[Output truncated to {max_length} chars. "
                "Suggest using filters or pagination.]"
            )

        if result.returncode == 0:
            logger.info(
                "KooCLI command succeeded",
                extra={"structured_extra": {
                    "service": service,
                    "operation": operation,
                    "output_len": len(output),
                }},
            )
            return f"Success:\n{output}"
        else:
            logger.warning(
                "KooCLI command failed",
                extra={"structured_extra": {
                    "service": service,
                    "operation": operation,
                    "returncode": result.returncode,
                }},
            )
            return f"Error (code {result.returncode}):\n{output}"

    except subprocess.TimeoutExpired:
        logger.error("KooCLI command timed out", extra={"structured_extra": {
            "service": service, "operation": operation,
            "timeout": _settings.koocli_timeout,
        }})
        return f"Error: Command timed out after {_settings.koocli_timeout}s."
    except FileNotFoundError:
        return "Error: 'hcloud' not found in PATH."
    except Exception as e:
        logger.exception("Unexpected KooCLI error")
        return f"Unexpected error: {str(e)}"
