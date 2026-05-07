import sys
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import uvicorn
from config.settings import get_settings

settings = get_settings()

print(f"=== Huawei Cloud Smart Assistant ===")
print(f"  Model:    {settings.llm_model}")
print(f"  API Base: {settings.open_api_base}")
print(f"  Region:   {settings.huawei_region}")
print(f"  AK:       {settings.huawei_ak[:6]}...")
print(f"  Port:     {settings.backend_port}")
print(f"====================================")

uvicorn.run(
    "app:app",
    host="0.0.0.0",
    port=settings.backend_port,
    reload=False,
)
