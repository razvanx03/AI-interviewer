import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from schemas.interview import InterviewCreate, InterviewResponse, InterviewStatus
from schemas.chat import ChatMessage, MessageRole, ChatResponse
from llm.base import BaseLLMProvider
from llm.mock_provider import MockLLMProvider

class InterviewSession:
    def __init__(self, data: InterviewCreate):
        self.id = str(uuid.uuid4())[:8]  # Clean 8-char shareable ID
        self.job_title = data.job_title
        self.company_name = data.company_name
        self.job_description = data.job_description
        self.experience_level = data.experience_level
        self.candidate_name = data.candidate_name or "Candidate"
        self.cv_filename = data.cv_filename
        self.cv_raw_text = data.cv_raw_text
        self.status = InterviewStatus.ACTIVE
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.messages: List[ChatMessage] = []
        self.total_questions = 0

class InterviewService:
    """
    Session and interview orchestrator.
    Manages in-memory storage (designed to be swapped with DB Repository).
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self._sessions: Dict[str, InterviewSession] = {}
        self.llm = llm_provider or MockLLMProvider()

    def create_interview(self, data: InterviewCreate) -> InterviewSession:
        session = InterviewSession(data)
        
        # Initial greeting and opening question
        company_phrase = f" at {session.company_name}" if session.company_name else ""
        intro_content = (
            f"Hello {session.candidate_name}! Welcome to your technical interview for the "
            f"**{session.job_title}** role{company_phrase}. "
            f"I have reviewed your resume and the job requirements.\n\n"
            f"To begin, could you introduce yourself briefly and highlight your background relevant to this position?"
        )
        
        initial_msg = ChatMessage(
            id=str(uuid.uuid4())[:8],
            role=MessageRole.ASSISTANT,
            content=intro_content,
            created_at=datetime.now(timezone.utc),
            question_number=1
        )
        session.messages.append(initial_msg)
        session.total_questions = 1
        
        self._sessions[session.id] = session
        return session

    def get_interview(self, interview_id: str) -> Optional[InterviewSession]:
        return self._sessions.get(interview_id)

    def list_interviews(self) -> List[InterviewSession]:
        return list(self._sessions.values())

    async def add_candidate_message_and_respond(
        self, 
        interview_id: str, 
        candidate_content: str
    ) -> Optional[ChatResponse]:
        session = self.get_interview(interview_id)
        if not session:
            return None

        # Add candidate message
        user_msg = ChatMessage(
            id=str(uuid.uuid4())[:8],
            role=MessageRole.USER,
            content=candidate_content,
            created_at=datetime.now(timezone.utc)
        )
        session.messages.append(user_msg)
        session.updated_at = datetime.now(timezone.utc)

        # Prepare context for LLM
        messages_payload = [{"role": m.role.value, "content": m.content} for m in session.messages]
        system_prompt = (
            f"You are an expert technical interviewer hiring for: {session.job_title}.\n"
            f"Job Description: {session.job_description}\n"
            f"Candidate CV Content: {session.cv_raw_text or 'Not provided'}\n"
            f"Evaluate responses concisely and ask the next focused question."
        )

        ai_text = await self.llm.generate_response(system_prompt, messages_payload)
        
        session.total_questions += 1
        is_complete = session.total_questions >= 6
        if is_complete:
            session.status = InterviewStatus.COMPLETED

        ai_msg = ChatMessage(
            id=str(uuid.uuid4())[:8],
            role=MessageRole.ASSISTANT,
            content=ai_text,
            created_at=datetime.now(timezone.utc),
            question_number=session.total_questions
        )
        session.messages.append(ai_msg)

        return ChatResponse(
            message=ai_msg,
            is_complete=is_complete,
            next_question_number=session.total_questions if not is_complete else None
        )

interview_service = InterviewService()
