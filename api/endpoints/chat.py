from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from schemas.chat import ChatRequest, ChatResponse
from services.interview_service import interview_service
import json

router = APIRouter()

@router.post("/{interview_id}/chat", response_model=ChatResponse)
async def send_message(interview_id: str, request: ChatRequest):
    """Send candidate response and receive AI interviewer feedback / next question."""
    response = await interview_service.add_candidate_message_and_respond(
        interview_id=interview_id,
        candidate_content=request.content
    )
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID '{interview_id}' was not found"
        )
    return response

@router.websocket("/{interview_id}/ws")
async def websocket_chat(websocket: WebSocket, interview_id: str):
    """
    WebSocket endpoint for real-time bidirectional interview chat / streaming.
    Prepared for token streaming and speech/audio pipeline in future iterations.
    """
    await websocket.accept()
    session = interview_service.get_interview(interview_id)
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

            # Stream response chunks or send completed response
            system_prompt = f"Technical Interviewer for {session.job_title}"
            stream_gen = interview_service.llm.generate_stream(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}]
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
