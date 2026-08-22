import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict, Tuple
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.interview import Interview
from models.message import Message
from models.candidate import Candidate
from schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewStatus,
    ExperienceLevel,
    CandidateItem,
    CandidateResponse,
)
from schemas.chat import ChatMessage, MessageRole, ChatResponse
from llm.base import BaseLLMProvider
from llm.mock_provider import MockLLMProvider

class InterviewService:
    """
    Session and interview orchestrator powered by PostgreSQL via SQLAlchemy AsyncSession.
    Supports multi-CV candidate screening, scoring, and automated top candidate selection.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or MockLLMProvider()

    def screen_candidates(
        self, job_title: str, job_description: str, experience_level: str, candidates: List[Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Evaluate and rank candidates against job requirements.
        Returns (top_candidate, screening_results).
        """
        results = []
        jd_words = set(re.findall(r'\b[a-zA-Z0-9+#.-]{3,}\b', (job_title + " " + job_description).lower()))

        tech_catalogue = [
            "React", "TypeScript", "JavaScript", "Python", "FastAPI", "Django", "Node.js",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS",
            "GCP", "GraphQL", "REST", "CI/CD", "Tailwind", "Next.js", "Java", "Go", "Rust"
        ]

        for cand in candidates:
            cand_name = cand.name if hasattr(cand, "name") else cand.get("name", "Candidate")
            cand_cv = cand.cv_raw_text if hasattr(cand, "cv_raw_text") else cand.get("cv_raw_text", "")
            cand_file = cand.cv_filename if hasattr(cand, "cv_filename") else cand.get("cv_filename")

            cv_text_lower = (cand_cv or "").lower()
            cv_words = set(re.findall(r'\b[a-zA-Z0-9+#.-]{3,}\b', cv_text_lower))

            matched_keywords = list(jd_words.intersection(cv_words))
            strengths = [t for t in tech_catalogue if t.lower() in cv_text_lower]

            if not strengths and matched_keywords:
                strengths = [kw.capitalize() for kw in matched_keywords[:4]]

            base_score = 65
            keyword_boost = min(len(matched_keywords) * 5, 25)
            strengths_boost = min(len(strengths) * 3, 10)
            match_score = min(base_score + keyword_boost + strengths_boost, 99)

            if len(strengths) > 0:
                summary = f"Strong alignment in {', '.join(strengths[:3])}. Demonstrated relevant background matching the job description."
            else:
                summary = "Solid general engineering foundation with adaptable skill set for the position."

            results.append({
                "name": cand_name,
                "cv_filename": cand_file,
                "cv_raw_text": cand_cv,
                "match_score": match_score,
                "strengths": strengths if strengths else ["Analytical Problem Solving", "System Design"],
                "summary": summary,
                "is_selected": False,
            })

        results.sort(key=lambda x: x["match_score"], reverse=True)
        if len(results) > 0:
            results[0]["is_selected"] = True
            top_candidate = results[0]
        else:
            top_candidate = {
                "name": "Candidate",
                "cv_filename": None,
                "cv_raw_text": None,
                "match_score": 90,
                "strengths": ["General Technical Aptitude"],
                "summary": "Direct applicant profile evaluated.",
                "is_selected": True,
            }

        return top_candidate, results

    async def create_interview(self, db: AsyncSession, data: InterviewCreate) -> Interview:
        interview_id = str(uuid.uuid4())[:8]  # Clean 8-char shareable ID
        now = datetime.now(timezone.utc)

        # Prepare candidate pool
        candidates_list = []
        if data.candidates and len(data.candidates) > 0:
            candidates_list = data.candidates
        else:
            candidates_list = [
                CandidateItem(
                    name=data.candidate_name or "Candidate",
                    cv_filename=data.cv_filename,
                    cv_raw_text=data.cv_raw_text,
                )
            ]

        exp_enum = (
            data.experience_level
            if isinstance(data.experience_level, ExperienceLevel)
            else ExperienceLevel(data.experience_level)
        )

        top_cand, screening_results = self.screen_candidates(
            job_title=data.job_title,
            job_description=data.job_description,
            experience_level=exp_enum.value,
            candidates=candidates_list,
        )

        interview = Interview(
            id=interview_id,
            job_title=data.job_title,
            company_name=data.company_name,
            job_description=data.job_description,
            experience_level=exp_enum,
            candidate_name=top_cand["name"],
            cv_filename=top_cand["cv_filename"],
            cv_raw_text=top_cand["cv_raw_text"],
            status=InterviewStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        db.add(interview)

        # Add relational Candidate entries
        for res in screening_results:
            cand_model = Candidate(
                id=str(uuid.uuid4())[:8],
                interview_id=interview_id,
                name=res["name"],
                cv_filename=res.get("cv_filename"),
                cv_raw_text=res.get("cv_raw_text"),
                match_score=res.get("match_score"),
                strengths=res.get("strengths", []),
                summary=res.get("summary"),
                is_selected=res.get("is_selected", False),
                created_at=now,
            )
            db.add(cand_model)

        # Create initial greeting and opening question
        company_phrase = f" at {interview.company_name}" if interview.company_name else ""
        screening_phrase = ""
        if len(candidates_list) > 1:
            screening_phrase = (
                f"After evaluating {len(candidates_list)} candidate resumes against our requirements, "
                f"your profile emerged as the top match ({top_cand['match_score']}% alignment).\n\n"
            )

        intro_content = (
            f"Hello {interview.candidate_name}! Welcome to your technical interview for the "
            f"**{interview.job_title}** role{company_phrase}. "
            f"{screening_phrase}"
            f"To begin, could you introduce yourself briefly and highlight your background relevant to this position?"
        )

        initial_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview.id,
            role=MessageRole.ASSISTANT,
            content=intro_content,
            question_number=1,
            created_at=now,
        )
        db.add(initial_msg)

        await db.commit()
        return await self.get_interview(db, interview.id)

    async def get_interview(self, db: AsyncSession, interview_id: str) -> Optional[Interview]:
        stmt = (
            select(Interview)
            .where(Interview.id == interview_id)
            .options(
                selectinload(Interview.messages),
                selectinload(Interview.candidates),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_interviews(
        self, db: AsyncSession, ids: Optional[List[str]] = None
    ) -> List[Interview]:
        stmt = (
            select(Interview)
            .options(
                selectinload(Interview.messages),
                selectinload(Interview.candidates),
            )
            .order_by(Interview.created_at.desc())
        )
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
                role=MessageRole(m.role) if isinstance(m.role, str) else m.role,
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
            role=MessageRole.USER,
            content=candidate_content,
            created_at=now,
        )
        db.add(user_msg)

        # Count questions asked so far
        assistant_questions = [
            m for m in interview.messages
            if (m.role == MessageRole.ASSISTANT or getattr(m.role, "value", None) == "assistant")
            and m.question_number
        ]
        next_q_num = len(assistant_questions) + 1
        is_complete = next_q_num > 5

        # 2. Build context for LLM
        history_payload = [
            {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
            for m in interview.messages
        ]
        history_payload.append({"role": MessageRole.USER.value, "content": candidate_content})

        system_prompt = (
            f"You are an expert technical interviewer hiring for: {interview.job_title}.\n"
            f"Job Description: {interview.job_description}\n"
            f"Candidate CV Content: {interview.cv_raw_text or 'Not provided'}\n"
            f"Evaluate responses concisely and ask the next focused question."
        )

        ai_text = await self.llm.generate_response(system_prompt, history_payload)

        if is_complete:
            interview.status = InterviewStatus.COMPLETED

        interview.updated_at = now

        ai_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT,
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
            role=MessageRole.USER,
            content=candidate_content,
            created_at=now,
        )
        db.add(user_msg)
        await db.commit()

        # Count questions
        assistant_questions = [
            m for m in interview.messages
            if (m.role == MessageRole.ASSISTANT or getattr(m.role, "value", None) == "assistant")
            and m.question_number
        ]
        next_q_num = len(assistant_questions) + 1
        is_complete = next_q_num > 5

        # 2. Build context for LLM
        history_payload = [
            {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
            for m in interview.messages
        ]
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
            role=MessageRole.ASSISTANT,
            content=full_ai_response.strip(),
            question_number=next_q_num if not is_complete else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ai_msg)

        if is_complete:
            interview.status = InterviewStatus.COMPLETED
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
        interview.status = InterviewStatus.COMPLETED
        interview.updated_at = now

        closing_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT,
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
    # ==============================================================================
    # [DEV ONLY - TEMPORARY TESTING METHOD TO BE REMOVED LATER]
    # ==============================================================================
    async def clear_all_data(self, db: AsyncSession) -> None:
        """Truncate all rows across interviews, candidates, and messages."""
        from sqlalchemy import text
        await db.execute(text("TRUNCATE TABLE interviews, candidates, messages CASCADE;"))
        await db.commit()

interview_service = InterviewService()
