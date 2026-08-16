import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.interview import Interview
from models.message import Message
from schemas.interview import InterviewCreate, InterviewResponse, InterviewStatus, ExperienceLevel
from schemas.chat import ChatMessage, MessageRole, ChatResponse
from llm.base import BaseLLMProvider
from llm.mock_provider import MockLLMProvider

class InterviewService:
    """
    Session and interview orchestrator powered by PostgreSQL via SQLAlchemy AsyncSession.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or MockLLMProvider()

    async def create_interview(self, db: AsyncSession, data: InterviewCreate) -> Interview:
        interview_id = str(uuid.uuid4())[:8]  # Clean 8-char shareable ID
        now = datetime.now(timezone.utc)

        interview = Interview(
            id=interview_id,
            job_title=data.job_title,
            company_name=data.company_name,
            job_description=data.job_description,
            experience_level=data.experience_level.value if isinstance(data.experience_level, ExperienceLevel) else str(data.experience_level),
            candidate_name=data.candidate_name or "Candidate",
            cv_filename=data.cv_filename,
            cv_raw_text=data.cv_raw_text,
            status=InterviewStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )
        db.add(interview)

        # Create initial greeting and opening question
        company_phrase = f" at {interview.company_name}" if interview.company_name else ""
        intro_content = (
            f"Hello {interview.candidate_name}! Welcome to your technical interview for the "
            f"**{interview.job_title}** role{company_phrase}. "
            f"I have reviewed your resume and the job requirements.\n\n"
            f"To begin, could you introduce yourself briefly and highlight your background relevant to this position?"
        )

        initial_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview.id,
            role=MessageRole.ASSISTANT.value,
            content=intro_content,
            question_number=1,
            created_at=now,
        )
        db.add(initial_msg)

        await db.commit()
        await db.refresh(interview)
        return interview

    async def get_interview(self, db: AsyncSession, interview_id: str) -> Optional[Interview]:
        stmt = (
            select(Interview)
            .where(Interview.id == interview_id)
            .options(selectinload(Interview.messages))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_interviews(
        self, db: AsyncSession, ids: Optional[List[str]] = None
    ) -> List[Interview]:
        stmt = select(Interview).options(selectinload(Interview.messages)).order_by(Interview.created_at.desc())
        if ids:
            stmt = stmt.where(Interview.id.in_(ids))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_messages(self, db: AsyncSession, interview_id: str) -> List[ChatMessage]:
        stmt = (
            select(Message)
            .where(Message.interview_id == interview_id)
            .order_by(Message.created_at.asc())
        )
        result = await db.execute(stmt)
        db_messages = result.scalars().all()
        return [
            ChatMessage(
                id=m.id,
                role=MessageRole(m.role),
                content=m.content,
                created_at=m.created_at,
                question_number=m.question_number,
                feedback=m.feedback,
            )
            for m in db_messages
        ]

    async def add_candidate_message_and_respond(
        self, db: AsyncSession, interview_id: str, candidate_content: str
    ) -> Optional[ChatResponse]:
        interview = await self.get_interview(db, interview_id)
        if not interview:
            return None

        now = datetime.now(timezone.utc)

        # 1. Insert user message
        user_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.USER.value,
            content=candidate_content,
            created_at=now,
        )
        db.add(user_msg)

        # Count questions asked so far
        assistant_questions = [m for m in interview.messages if m.role == MessageRole.ASSISTANT.value and m.question_number]
        next_q_num = len(assistant_questions) + 1
        is_complete = next_q_num > 5

        # 2. Build context for LLM
        history_payload = [{"role": m.role, "content": m.content} for m in interview.messages]
        history_payload.append({"role": MessageRole.USER.value, "content": candidate_content})

        system_prompt = (
            f"You are an expert technical interviewer hiring for: {interview.job_title}.\n"
            f"Job Description: {interview.job_description}\n"
            f"Candidate CV Content: {interview.cv_raw_text or 'Not provided'}\n"
            f"Evaluate responses concisely and ask the next focused question."
        )

        ai_text = await self.llm.generate_response(system_prompt, history_payload)

        if is_complete:
            interview.status = InterviewStatus.COMPLETED.value

        interview.updated_at = now

        ai_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT.value,
            content=ai_text,
            question_number=next_q_num if not is_complete else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ai_msg)

        await db.commit()

        return ChatResponse(
            message=ChatMessage(
                id=ai_msg.id,
                role=MessageRole.ASSISTANT,
                content=ai_msg.content,
                created_at=ai_msg.created_at,
                question_number=ai_msg.question_number,
            ),
            is_complete=is_complete,
            next_question_number=next_q_num if not is_complete else None,
        )

    async def stream_candidate_message_and_respond(
        self, db: AsyncSession, interview_id: str, candidate_content: str
    ):
        interview = await self.get_interview(db, interview_id)
        if not interview:
            return

        now = datetime.now(timezone.utc)

        # 1. Insert user message to database
        user_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.USER.value,
            content=candidate_content,
            created_at=now,
        )
        db.add(user_msg)
        await db.commit()

        # Count questions
        assistant_questions = [m for m in interview.messages if m.role == MessageRole.ASSISTANT.value and m.question_number]
        next_q_num = len(assistant_questions) + 1
        is_complete = next_q_num > 5

        # 2. Build context for LLM
        history_payload = [{"role": m.role, "content": m.content} for m in interview.messages]
        history_payload.append({"role": MessageRole.USER.value, "content": candidate_content})

        system_prompt = (
            f"You are an expert technical interviewer hiring for: {interview.job_title}.\n"
            f"Job Description: {interview.job_description}\n"
            f"Candidate CV Content: {interview.cv_raw_text or 'Not provided'}\n"
            f"Evaluate responses concisely and ask the next focused question."
        )

        full_ai_response = ""
        stream_gen = self.llm.generate_stream(system_prompt, history_payload)

        async for chunk in stream_gen:
            full_ai_response += chunk
            yield {"chunk": chunk, "is_complete": False}

        # 3. Save assistant message to database
        ai_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT.value,
            content=full_ai_response.strip(),
            question_number=next_q_num if not is_complete else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ai_msg)

        if is_complete:
            interview.status = InterviewStatus.COMPLETED.value
        interview.updated_at = datetime.now(timezone.utc)

        await db.commit()

        yield {
            "chunk": "",
            "is_complete": is_complete,
            "message_id": ai_msg.id,
            "question_number": ai_msg.question_number,
            "done": True,
        }

    async def delete_interview(self, db: AsyncSession, interview_id: str) -> bool:
        stmt = delete(Interview).where(Interview.id == interview_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    async def complete_interview(self, db: AsyncSession, interview_id: str) -> Optional[Interview]:
        """Mark an interview as completed and append a closing acknowledgment message."""
        interview = await self.get_interview(db, interview_id)
        if not interview:
            return None

        now = datetime.now(timezone.utc)
        interview.status = InterviewStatus.COMPLETED.value
        interview.updated_at = now

        closing_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT.value,
            content=(
                f"Thank you, {interview.candidate_name}! The interview session for the **{interview.job_title}** position has concluded. "
                f"Your answers and transcript have been securely recorded."
            ),
            question_number=None,
            created_at=now,
        )
        db.add(closing_msg)
        await db.commit()
        await db.refresh(interview)
        return interview

interview_service = InterviewService()
