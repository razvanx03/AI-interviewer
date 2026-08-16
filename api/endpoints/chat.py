from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json

from db.session import get_db, async_session_maker
from schemas.chat import ChatRequest, ChatResponse
from services.interview_service import interview_service

router = APIRouter()

@router.post("/{interview_id}/chat", response_model=ChatResponse)
async def send_message(
    interview_id: str, request: ChatRequest, db: AsyncSession = Depends(get_db)
):
    """Send candidate response and receive AI interviewer feedback / next question, saving to PostgreSQL."""
    response = await interview_service.add_candidate_message_and_respond(
        db=db,
        interview_id=interview_id,
        candidate_content=request.content,
    )
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID '{interview_id}' was not found",
        )
    return response

@router.post("/{interview_id}/stream")
async def stream_chat(
    interview_id: str, request: ChatRequest, db: AsyncSession = Depends(get_db)
):
    """
    Stream candidate message and receive real-time token-by-token SSE response from AI interviewer.
    Saves candidate response and full assistant reply to PostgreSQL database.
    """
    session = await interview_service.get_interview(db, interview_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID '{interview_id}' was not found",
        )

    async def event_generator():
        async for event in interview_service.stream_candidate_message_and_respond(
            db=db, interview_id=interview_id, candidate_content=request.content
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.websocket("/{interview_id}/ws")
async def websocket_chat(websocket: WebSocket, interview_id: str):
    """
    WebSocket endpoint for real-time bidirectional interview chat / streaming.
    Prepared for token streaming and speech/audio pipeline.
    """
    await websocket.accept()
    async with async_session_maker() as db:
        session = await interview_service.get_interview(db, interview_id)
        if not session:
            await websocket.send_json({"error": "Interview session not found"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            user_message = data.get("content", "").strip()

            if not user_message:
                continue

            system_prompt = f"Technical Interviewer for {session.job_title}"
            stream_gen = interview_service.llm.generate_stream(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            await websocket.send_json({"type": "stream_start"})
            full_response = ""
            async for chunk in stream_gen:
                full_response += chunk
                await websocket.send_json({"type": "chunk", "content": chunk})

            await websocket.send_json({"type": "stream_end", "full_content": full_response})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "detail": str(e)})
