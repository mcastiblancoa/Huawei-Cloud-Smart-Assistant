import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load from the consolidated root .env (3 levels up: core -> app -> backend -> huawei_cloud_smart_assistant -> root)
_root_env = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(_root_env)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_root_env),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Huawei Cloud Smart Assistant"
    app_env: str = "local"
    backend_cors_origins: str = "http://localhost:5173"

    # Huawei Cloud SIS / IAM configuration
    huawei_region: str = os.getenv("HUAWEI_REGION")
    huawei_project_id: str = os.getenv("HUAWEI_PROJECT_ID")
    huawei_iam_endpoint: str = os.getenv("HUAWEI_IAM_ENDPOINT")
    huawei_sis_endpoint: str = os.getenv("HUAWEI_SIS_ENDPOINT")
    huawei_username: str = os.getenv("HUAWEI_USERNAME")
    huawei_password: str = os.getenv("HUAWEI_PASSWORD")
    huawei_domain_name: str = os.getenv("HUAWEI_DOMAIN_NAME")

    # Huawei Cloud SDK configuration (for RMS)
    cloud_sdk_ak: str = os.getenv("HUAWEI_AK")
    cloud_sdk_sk: str = os.getenv("HUAWEI_SK")
    cloud_sdk_domain_id: str = os.getenv("CLOUD_SDK_DOMAIN_ID")

    # Speech parameters
    # Default may vary by account/region. If invalid, backend can try fallbacks.
    sis_property: str = os.getenv("SIS_PROPERTY")
    sis_fallback_properties: str = "english_8k_common"
    sis_add_punc: str = "yes"
    sis_digit_norm: str = "yes"
    sis_need_word_info: str = "no"

    # MaaS configuration
    maas_api_url: str = os.getenv("MAAS_API_URL")
    maas_api_key: str = os.getenv("MAAS_API_KEY")

    # Whisper ASR configuration
    whisper_asr_url: str = os.getenv("WHISPER_ASR_URL")

    max_upload_mb: int = 5
    temp_dir: str = "tmp_audio"


@lru_cache
def get_settings() -> Settings:
    return Settings()
