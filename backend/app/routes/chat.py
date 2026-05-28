"""SSE streaming chat endpoint."""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import ChatRequest
from ..services.conversation import ConversationRunner

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream chat responses via Server-Sent Events.

    Event types: plan, message, tool, meta, error, done
    """
    runner = ConversationRunner()

    async def generate():
        try:
            async for event_type, data in runner.run(
                user_message=req.message,
                files=req.files,
                history=[h.model_dump() for h in req.history],
            ):
                yield f"event: {event_type}\ndata: {data}\n\n"
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"event: error\ndata: {json.dumps({'msg': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
