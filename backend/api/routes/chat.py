from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models.schemas import ChatRequest, ChatResponse
from api.chat import run_chat_turn
from config.logging import get_logger

logger = get_logger("api.chat_route")
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    logger.info(
        "Chat request received",
        extra={"structured_extra": {
            "session_id": request.session_id,
            "message": request.message[:100],
        }},
    )
    try:
        result = run_chat_turn(request.message, request.session_id)
        logger.info(
            "Chat response generated",
            extra={"structured_extra": {
                "session_id": request.session_id,
                "reply_preview": result["reply"][:100] if result["reply"] else "EMPTY",
            }},
        )
        return ChatResponse(
            session_id=request.session_id,
            reply=result["reply"],
            raw_messages=result.get("raw_messages"),
        )
    except Exception as exc:
        logger.exception("Chat endpoint error")
        return ChatResponse(
            session_id=request.session_id,
            reply=f"Error processing your request. Please try again.",
            raw_messages=None,
        )
