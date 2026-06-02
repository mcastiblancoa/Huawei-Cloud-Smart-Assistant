from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from config.logging import setup_logging, get_logger
from api.routes import health_router, chat_router, voice_router, vision_router

settings = get_settings()
setup_logging(level="INFO", env=settings.app_env)

logger = get_logger("app")

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.backend_cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(chat_router, tags=["chat"])
app.include_router(voice_router, tags=["voice"])
app.include_router(vision_router, tags=["vision"])

logger.info(
    "Huawei Cloud Smart Assistant started",
    extra={"structured_extra": {
        "app_name": settings.app_name,
        "env": settings.app_env,
        "port": settings.backend_port,
    }},
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=not settings.is_production,
    )
