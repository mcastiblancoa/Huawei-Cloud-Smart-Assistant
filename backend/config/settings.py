import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

_ROOT_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _ROOT_DIR / ".env"
load_dotenv(_ENV_FILE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Huawei Cloud Smart Assistant"
    app_env: str = "local"
    backend_cors_origins: str = "http://localhost:5173"
    backend_port: int = 8003

    huawei_region: str = "ap-southeast-3"
    huawei_project_id: str = ""
    huawei_project_id_sis: str = ""
    huawei_ak: str = ""
    huawei_sk: str = ""
    cloud_sdk_domain_id: str = ""

    huawei_iam_endpoint: str = ""
    huawei_sis_endpoint: str = ""
    huawei_username: str = ""
    huawei_password: str = ""
    huawei_domain_name: str = ""

    sis_property: str = "english_16k_common"
    sis_fallback_properties: str = "english_8k_common"
    sis_add_punc: str = "yes"
    sis_digit_norm: str = "yes"
    sis_need_word_info: str = "no"

    maas_api_url: str = ""
    maas_api_key: str = ""
    open_api_base: str = ""
    llm_model: str = "glm-5.1" #deepseek-v3.2
    intent_model: str = "glm-5.1" #deepseek-v3.2

    whisper_asr_url: str = ""

    kokoro_speech_url: str = ""
    kokoro_voice_es: str = "af_heart"
    kokoro_voice_en: str = "af_bella"
    kokoro_lang_code_es: str = "es"
    kokoro_lang_code_en: str = "en-us"
    kokoro_response_format: str = "mp3"
    kokoro_speed: float = 1.0
    kokoro_timeout: int = 30
    kokoro_max_retries: int = 2

    max_upload_mb: int = 5
    temp_dir: str = "tmp_audio"

    schema_data_dir: str = str(_ROOT_DIR / "backend" / "schemas" / "data")

    koocli_timeout: int = 180
    koocli_max_output: int = 100000
    koocli_max_retries: int = 2

    cache_ttl_seconds: int = 30
    cache_max_entries: int = 200
    max_graph_iterations: int = 80

    @property
    def root_dir(self) -> Path:
        return _ROOT_DIR

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
