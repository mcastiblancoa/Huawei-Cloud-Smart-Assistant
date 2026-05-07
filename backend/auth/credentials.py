from config.settings import get_settings

_settings = get_settings()


def get_credentials() -> dict[str, str]:
    return {
        "ak": _settings.huawei_ak,
        "sk": _settings.huawei_sk,
        "region": _settings.huawei_region,
        "project_id": _settings.huawei_project_id,
        "domain_id": _settings.cloud_sdk_domain_id,
    }


def validate_credentials() -> bool:
    creds = get_credentials()
    return bool(creds["ak"] and creds["sk"] and creds["region"])
