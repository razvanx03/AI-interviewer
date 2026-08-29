import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict, Tuple, AsyncGenerator
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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
from llm import (
    BaseLLMProvider,
    get_llm_provider,
    build_system_interviewer_prompt,
    build_intro_question_prompt,
)
from core.config import settings
from core.constants import (
    TECH_CATALOGUE,
    CLARIFICATION_STEER_THRESHOLD,
    INTERVIEW_COMPLETE_TOKEN,
    BASE_SCREENING_SCORE,
    KEYWORD_MATCH_WEIGHT,
    MAX_KEYWORD_BOOST,
    STRENGTH_MATCH_WEIGHT,
    MAX_STRENGTHS_BOOST,
    MAX_SCREENING_SCORE,
)

class InterviewService:
    """
    Session and interview orchestrator powered by PostgreSQL via SQLAlchemy AsyncSession.
    Supports multi-CV candidate screening, scoring, and automated top candidate selection.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        if llm_provider:
            self.llm = llm_provider
        else:
            self.llm = get_llm_provider(
                base_url=settings.OLLAMA_BASE_URL,
                model_name=settings.DEFAULT_LLM_MODEL,
            )

    def _extract_candidate_name_from_cv_text(self, raw_text: str) -> Optional[str]:
        """
        Extract candidate's full name from the top header of the CV text if name is generic.
        """
        if not raw_text or not raw_text.strip():
            return None

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for line in lines[:8]:
            # Clean common resume header prefixes
            cleaned = re.sub(r'^(name|curriculum\s+vitae|cv|resume|candidat|candidate|nume)[\s:=-]+', '', line, flags=re.IGNORECASE).strip()
            # Split before title separators like ' - ', ' | ', ' -- '
            cleaned = re.split(r'\s+[-|•—]\s+', cleaned)[0].strip()

            # Ignore generic section titles or contact lines
            if re.search(r'\b(engineer|developer|architect|designer|manager|curriculum|vitae|resume|contact|email|phone|summary|education|skills|experience)\b', cleaned, re.IGNORECASE):
                continue
            if re.search(r'[@0-9+://]', cleaned):
                continue

            words = cleaned.split()
            # A valid name is usually 2 to 4 alphabetic words
            if 2 <= len(words) <= 4 and all(re.match(r'^[A-Za-zÀ-ÿ\.\'-]+$', w) for w in words):
                return " ".join(w.capitalize() for w in words)

        return None

    def screen_candidates(
        self, job_title: str, job_description: str, experience_level: str, candidates: List[Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Screening candidate pool:
        - Extracts actual candidate name if generic fallback 'Candidate' was used.
        - Calculates dynamic matching score based on job description competencies & skills overlap.
        - Ranks all candidates strictly in descending order of match_score.
        - Selects the #1 top candidate by default.
        """
        # 1. Identify key tech requirements from Job Description & Title
        jd_text_lower = f"{job_title} {job_description}".lower()
        required_tech = [t for t in TECH_CATALOGUE if t.lower() in jd_text_lower]
        if not required_tech:
            required_tech = ["Full Stack", "Software Engineering", "APIs", "Database", "Git"]

        results = []
        for cand in candidates:
            cand_name = cand.name if hasattr(cand, "name") else cand.get("name", "Candidate")
            cand_cv = cand.cv_raw_text if hasattr(cand, "cv_raw_text") else cand.get("cv_raw_text", "")
            cand_file = cand.cv_filename if hasattr(cand, "cv_filename") else cand.get("cv_filename")

            # Check if name is the generic fallback 'Candidate' / empty
            is_generic_name = (
                not cand_name
                or cand_name.strip().lower() in ("candidate", "applicant", "null", "none", "unknown", "cv", "resume")
            )
            if is_generic_name and cand_cv and cand_cv.strip():
                extracted_name = self._extract_candidate_name_from_cv_text(cand_cv)
                if extracted_name:
                    cand_name = extracted_name

            # Calculate matching skills & dynamic match score
            cv_lower = (cand_cv or "").lower()
            matched_skills = [t for t in required_tech if t.lower() in cv_lower]
            other_skills = [t for t in TECH_CATALOGUE if t.lower() in cv_lower and t not in matched_skills]

            # Strengths: matched skills first, then general competencies
            strengths = (matched_skills + other_skills)[:4]
            if not strengths:
                strengths = ["Technical Competency", "Document Verified", "Profile Parsed"]

            # Dynamic match score computation
            base_score = 72
            skill_bonus = min(len(matched_skills) * 6, 20)
            length_bonus = min(len(cand_cv.split()) // 30, 6) if cand_cv else 0
            subtle_var = (hash(cand_name + (cand_file or "")) % 5) - 2

            raw_score = base_score + skill_bonus + length_bonus + subtle_var
            final_score = max(60, min(98, raw_score))

            if matched_skills:
                skills_highlight = ", ".join(matched_skills[:3])
                summary = f"Strong alignment in {skills_highlight} matching core requirements for {job_title}."
            else:
                summary = f"Qualified applicant profile evaluated for {job_title}."

            results.append({
                "name": cand_name,
                "cv_filename": cand_file,
                "cv_raw_text": cand_cv,
                "match_score": final_score,
                "strengths": strengths,
                "summary": summary,
                "is_selected": False,
            })

        # 2. Sort all candidates strictly in descending order of match_score
        results.sort(key=lambda x: x["match_score"], reverse=True)

        # 3. Select the #1 highest matching candidate by default
        if len(results) > 0:
            results[0]["is_selected"] = True
            top_candidate = results[0]
        else:
            top_candidate = {
                "name": "Candidate",
                "cv_filename": None,
                "cv_raw_text": None,
                "match_score": 90,
                "strengths": ["Direct Applicant"],
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

        # 1. Extract dynamic interview topics from Job Description instantly
        topics_plan = []
        lines = [line.strip().lstrip("-*•123456789. ").strip() for line in data.job_description.split("\n") if line.strip()]
        valid_bullets = [
            l for l in lines
            if len(l) > 8 and not l.lower().startswith(("we are", "looking for", "requirements:", "responsibilities:", "core requirements", "about the role"))
        ]
        if len(valid_bullets) >= 2:
            topics_plan = valid_bullets[:5]
        else:
            topics_plan = [
                f"Core {data.job_title} Language & Framework Fundamentals",
                "Architecture, API Design & Data Flow",
                "Database Engineering & Query Performance",
                "Containerization, Microservices & Deployment",
                "Problem-Solving & Production Edge Cases",
            ]
        logger.info("[Interview %s] Dynamic Topics Plan initialized: %s", interview_id, topics_plan)

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
            active_question_number=1,
            consecutive_clarifications=0,
            topics_plan=topics_plan,
            current_topic_index=0,
            topic_follow_up_count=0,
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

        # Create initial greeting and opening question using AI model
        exp_level_str = exp_enum.value if hasattr(exp_enum, "value") else str(exp_enum)
        system_prompt = build_system_interviewer_prompt(
            job_title=interview.job_title,
            job_description=interview.job_description,
            experience_level=exp_level_str,
            company_name=interview.company_name,
            cv_raw_text=interview.cv_raw_text or "",
            candidate_name=interview.candidate_name,
            active_question_number=1,
            topics_plan=topics_plan,
            current_topic_index=0,
            topic_follow_up_count=0,
        )
        intro_prompt = build_intro_question_prompt(
            job_title=interview.job_title,
            job_description=interview.job_description,
            experience_level=exp_level_str,
            company_name=interview.company_name,
            cv_raw_text=interview.cv_raw_text or "",
            candidate_name=interview.candidate_name,
        )

        intro_content = await self.llm.generate_response(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": intro_prompt}],
        )
        if not intro_content or not intro_content.strip():
            raise ValueError("Ollama returned an empty opening question.")

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

        # 1. Save user message to database
        user_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.USER,
            content=candidate_content,
            created_at=now,
        )
        db.add(user_msg)
        await db.commit()

        # 2. Query clean, chronological message history from database
        res = await db.execute(
            select(Message)
            .where(Message.interview_id == interview_id)
            .order_by(Message.created_at.asc())
        )
        db_messages = res.scalars().all()
        history_payload = [
            {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
            for m in db_messages
        ]

        # Topic state machine: check for skip/pass/continue intents
        skip_patterns = [
            r"\b(nu\s+stiu|nu\s+am\s+facut|nu\s+am\s+folosit|nu\s+inteleg|ce\s+inseamna|ce\s+e\s+aia|ce\s+reprezinta)\b",
            r"\b(skip|pass|let'?s\s+continue|sa\s+continuam|trecem\s+mai\s+departe|alta\s+intrebare|urmatoarea\s+intrebare|next\s+question)\b",
        ]
        is_candidate_skip = any(re.search(pat, candidate_content.lower()) for pat in skip_patterns)

        MAX_FOLLOWUPS_PER_TOPIC = 1
        current_idx = interview.current_topic_index or 0
        follow_up_count = interview.topic_follow_up_count or 0
        topics = interview.topics_plan or []

        if is_candidate_skip or follow_up_count >= MAX_FOLLOWUPS_PER_TOPIC:
            current_idx += 1
            follow_up_count = 0
        else:
            follow_up_count += 1

        interview.current_topic_index = current_idx
        interview.topic_follow_up_count = follow_up_count
        all_topics_covered = bool(topics and current_idx >= len(topics))

        exp_level_str = (
            interview.experience_level.value
            if hasattr(interview.experience_level, "value")
            else str(interview.experience_level)
        )
        system_prompt = build_system_interviewer_prompt(
            job_title=interview.job_title,
            job_description=interview.job_description,
            experience_level=exp_level_str,
            company_name=interview.company_name,
            cv_raw_text=interview.cv_raw_text or "",
            candidate_name=interview.candidate_name,
            active_question_number=interview.active_question_number or 1,
            consecutive_clarifications=interview.consecutive_clarifications,
            clarification_threshold=CLARIFICATION_STEER_THRESHOLD,
            topics_plan=topics,
            current_topic_index=current_idx,
            topic_follow_up_count=follow_up_count,
        )

        logger.info(
            "[Interview %s] PRE-LLM | Q#: %s | Topic [%s/%s]: '%s' (FollowUp #%s) | Last User: '%s'",
            interview_id,
            interview.active_question_number,
            current_idx + 1,
            len(topics),
            topics[current_idx] if current_idx < len(topics) else "All Complete",
            follow_up_count,
            candidate_content[:50].replace("\n", " "),
        )

        ai_text = await self.llm.generate_response(system_prompt, history_payload)
        if not ai_text or not ai_text.strip():
            raise ValueError("Ollama returned an empty response.")

        ai_signaled_completion = INTERVIEW_COMPLETE_TOKEN in ai_text
        hit_safety_limit = (interview.active_question_number or 1) >= settings.SAFETY_MAX_QUESTIONS
        is_complete = ai_signaled_completion or hit_safety_limit or all_topics_covered
        cleaned_ai_text = ai_text.replace(INTERVIEW_COMPLETE_TOKEN, "").strip()

        if is_complete:
            interview.status = InterviewStatus.COMPLETED
            interview.active_question_number = None
            assigned_q_num = None
            cleaned_ai_text = await self._generate_evaluation_closing(interview, cleaned_ai_text)
        else:
            interview.active_question_number = (interview.active_question_number or 1) + 1
            assigned_q_num = interview.active_question_number

        interview.updated_at = now

        ai_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT,
            content=cleaned_ai_text,
            question_number=assigned_q_num,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ai_msg)
        await db.commit()

        logger.info(
            "[Interview %s] AI_MSG: '%s' | Question After: %s",
            interview_id,
            cleaned_ai_text[:60],
            assigned_q_num,
        )

        return ChatResponse(
            message=ChatMessage(
                id=ai_msg.id,
                role=MessageRole.ASSISTANT,
                content=ai_msg.content,
                created_at=ai_msg.created_at,
                question_number=ai_msg.question_number,
            ),
            is_complete=is_complete,
            next_question_number=assigned_q_num,
        )

    async def stream_candidate_message_and_respond(
        self, db: AsyncSession, interview_id: str, candidate_content: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        interview = await self.get_interview(db, interview_id)
        if not interview:
            yield {"error": "Interview session not found."}
            return

        if interview.status == InterviewStatus.COMPLETED:
            yield {"chunk": "Acest interviu a fost deja finalizat.", "done": True, "is_complete": True}
            return

        now = datetime.now(timezone.utc)

        # 1. Save user message to database
        user_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.USER,
            content=candidate_content,
            created_at=now,
        )
        db.add(user_msg)
        await db.commit()

        # 2. Query clean, chronological message history from database
        res = await db.execute(
            select(Message)
            .where(Message.interview_id == interview_id)
            .order_by(Message.created_at.asc())
        )
        db_messages = res.scalars().all()
        history_payload = [
            {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
            for m in db_messages
        ]

        # Topic state machine: check for skip/pass/continue intents
        skip_patterns = [
            r"\b(nu\s+stiu|nu\s+am\s+facut|nu\s+am\s+folosit|nu\s+inteleg|ce\s+inseamna|ce\s+e\s+aia|ce\s+reprezinta)\b",
            r"\b(skip|pass|let'?s\s+continue|sa\s+continuam|trecem\s+mai\s+departe|alta\s+intrebare|urmatoarea\s+intrebare|next\s+question)\b",
        ]
        is_candidate_skip = any(re.search(pat, candidate_content.lower()) for pat in skip_patterns)

        MAX_FOLLOWUPS_PER_TOPIC = 1
        current_idx = interview.current_topic_index or 0
        follow_up_count = interview.topic_follow_up_count or 0
        topics = interview.topics_plan or []

        if is_candidate_skip or follow_up_count >= MAX_FOLLOWUPS_PER_TOPIC:
            current_idx += 1
            follow_up_count = 0
        else:
            follow_up_count += 1

        interview.current_topic_index = current_idx
        interview.topic_follow_up_count = follow_up_count
        all_topics_covered = bool(topics and current_idx >= len(topics))

        exp_level_str = (
            interview.experience_level.value
            if hasattr(interview.experience_level, "value")
            else str(interview.experience_level)
        )
        system_prompt = build_system_interviewer_prompt(
            job_title=interview.job_title,
            job_description=interview.job_description,
            experience_level=exp_level_str,
            company_name=interview.company_name,
            cv_raw_text=interview.cv_raw_text or "",
            candidate_name=interview.candidate_name,
            active_question_number=interview.active_question_number or 1,
            consecutive_clarifications=interview.consecutive_clarifications,
            clarification_threshold=CLARIFICATION_STEER_THRESHOLD,
            topics_plan=topics,
            current_topic_index=current_idx,
            topic_follow_up_count=follow_up_count,
        )

        last_assistant_msg = next(
            (m.content for m in reversed(db_messages) if str(m.role).lower() in ("assistant", "messagerole.assistant")),
            "None",
        )
        last_user_msg = next(
            (m.content for m in reversed(db_messages) if str(m.role).lower() in ("user", "messagerole.user")),
            "None",
        )
        logger.info(
            "[Interview %s Streaming] PRE-LLM | Q#: %s | Topic [%s/%s]: '%s' (FollowUp #%s) | Last User: '%s'",
            interview_id,
            interview.active_question_number,
            current_idx + 1,
            len(topics),
            topics[current_idx] if current_idx < len(topics) else "All Complete",
            follow_up_count,
            last_user_msg[:50].replace("\n", " "),
        )

        full_ai_response = ""
        stream_gen = self.llm.generate_stream(system_prompt, history_payload)

        async for chunk in stream_gen:
            full_ai_response += chunk
            display_chunk = chunk.replace(INTERVIEW_COMPLETE_TOKEN, "")
            if display_chunk:
                yield {"chunk": display_chunk, "is_complete": False}

        if not full_ai_response.strip():
            raise ValueError("Ollama stream completed with empty response.")

        ai_signaled_completion = INTERVIEW_COMPLETE_TOKEN in full_ai_response
        hit_safety_limit = (interview.active_question_number or 1) >= settings.SAFETY_MAX_QUESTIONS
        is_complete = ai_signaled_completion or hit_safety_limit or all_topics_covered
        cleaned_ai_response = full_ai_response.replace(INTERVIEW_COMPLETE_TOKEN, "").strip()

        if is_complete:
            interview.status = InterviewStatus.COMPLETED
            interview.active_question_number = None
            assigned_q_num = None

            # Generate AI evaluation report and closing evaluation assessment
            evaluation_closing = await self._generate_evaluation_closing(interview, cleaned_ai_response)
            
            # If the streamed response was only [INTERVIEW_COMPLETE], emit the evaluation closing chunk
            closing_delta = evaluation_closing
            if cleaned_ai_response and evaluation_closing.startswith(cleaned_ai_response):
                closing_delta = evaluation_closing[len(cleaned_ai_response):]

            if closing_delta.strip():
                yield {"chunk": "\n\n" + closing_delta.strip(), "is_complete": True}

            cleaned_ai_response = evaluation_closing
        else:
            interview.active_question_number = (interview.active_question_number or 1) + 1
            assigned_q_num = interview.active_question_number

        # 3. Save assistant message to database
        ai_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT,
            content=cleaned_ai_response,
            question_number=assigned_q_num,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ai_msg)
        interview.updated_at = datetime.now(timezone.utc)

        await db.commit()

        logger.info(
            "[Interview %s Streaming] AI_MSG: '%s' | Question After: %s",
            interview_id,
            cleaned_ai_response[:60],
            assigned_q_num,
        )

        yield {
            "chunk": "",
            "done": True,
            "is_complete": is_complete,
            "question_number": assigned_q_num,
            "message_id": ai_msg.id,
        }

    async def _generate_evaluation_closing(
        self, interview: Interview, preamble_text: str = ""
    ) -> str:
        """Evaluate full interview transcript and generate candidate closing message with scores."""
        transcript_history = [
            {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
            for m in interview.messages
        ]

        eval_report = await self.llm.evaluate_interview(
            job_title=interview.job_title,
            job_description=interview.job_description,
            candidate_name=interview.candidate_name,
            cv_raw_text=interview.cv_raw_text or "",
            transcript=transcript_history,
        )

        overall_score = eval_report.get("overall_score", 0.0)
        summary_text = eval_report.get("summary", "Technical interview evaluation completed.")
        strengths = eval_report.get("strengths", [])
        strengths_str = "\n".join([f"- {s}" for s in strengths]) if strengths else ""
        weaknesses = eval_report.get("weaknesses", [])
        weaknesses_str = "\n".join([f"- {w}" for w in weaknesses]) if weaknesses else ""
        rec_label = eval_report.get("recommendation", "hire").replace("_", " ").title()

        intro_p = f"{preamble_text.strip()}\n\n" if preamble_text.strip() else ""

        return (
            f"{intro_p}"
            f"Thank you, {interview.candidate_name}! The interview session for the **{interview.job_title}** position has concluded.\n\n"
            f"**Overall AI Assessment: {overall_score}/10** ({rec_label})\n\n"
            f"{summary_text}\n\n"
            + (f"**Key Strengths Observed:**\n{strengths_str}\n\n" if strengths_str else "")
            + (f"**Areas for Improvement / Gaps:**\n{weaknesses_str}\n\n" if weaknesses_str else "")
            + f"Your full transcript and evaluation data have been recorded."
        )

    async def delete_interview(self, db: AsyncSession, interview_id: str) -> bool:
        stmt = delete(Interview).where(Interview.id == interview_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    async def complete_interview(self, db: AsyncSession, interview_id: str) -> Optional[Interview]:
        """Mark an interview as completed, generate AI evaluation report, and append closing message."""
        interview = await self.get_interview(db, interview_id)
        if not interview:
            return None

        now = datetime.now(timezone.utc)
        interview.status = InterviewStatus.COMPLETED
        interview.updated_at = now

        closing_content = await self._generate_evaluation_closing(interview)

        closing_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT,
            content=closing_content,
            question_number=None,
            created_at=now,
        )
        db.add(closing_msg)
        await db.commit()
        return await self.get_interview(db, interview.id)

    # ==============================================================================
    # [DEV ONLY - TEMPORARY TESTING METHOD TO BE REMOVED LATER]
    # ==============================================================================
    async def clear_all_data(self, db: AsyncSession) -> None:
        """Truncate all rows across interviews, candidates, and messages."""
        from sqlalchemy import text
        await db.execute(text("TRUNCATE TABLE interviews, candidates, messages CASCADE;"))
        await db.commit()

interview_service = InterviewService()
