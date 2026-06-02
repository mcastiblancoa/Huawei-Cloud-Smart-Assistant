from .health import router as health_router
from .chat import router as chat_router
from .voice import router as voice_router
from .vision import router as vision_router

__all__ = ["health_router", "chat_router", "voice_router", "vision_router"]
