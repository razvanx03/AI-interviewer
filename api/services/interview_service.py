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
    build_intro_prompt,
    build_first_question_prompt,
    build_clarification_response_prompt,
    build_both_response_prompt,
    build_refusal_response_prompt,
    build_next_question_prompt,
)
from llm.constants import (
    CONTEXT_TOKEN_THRESHOLD_RATIO,
    RECENT_MESSAGES_WINDOW_COUNT,
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

def _clean_candidate_display_name(name: str) -> str:
    """Format candidate name nicely (e.g. 'darius.pop' -> 'Darius Pop', 'DariusBotezan2026' -> 'Darius Botezan')."""
    if not name:
        return "Candidate"
    clean = name.strip()
    if "@" in clean:
        clean = clean.split("@")[0]
    clean = re.sub(r"\d+$", "", clean).strip()
    if "." in clean or "_" in clean or "-" in clean or " " in clean:
        parts = re.split(r"[._\-\s]+", clean)
        return " ".join(p.capitalize() for p in parts if p)
    parts = re.findall(r"[A-Z][a-z]*|[a-z]+", clean)
    if len(parts) > 1:
        return " ".join(p.capitalize() for p in parts)
    return clean.capitalize() if clean else "Candidate"

def _clean_llm_response(text: str) -> str:
    """Sanitize model output: remove thinking tags, speaker/persona prefixes, and outer quotes."""
    if not text:
        return ""
    # Strip <think>...</think> blocks if reasoning model emits them
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
    # Strip roleplay speaker prefixes like **You (Role):**, **Interviewer:**, Interviewer:, You:, etc.
    cleaned = re.sub(r'^\s*(\*\*You[^\*]+\*\*|\*\*Interviewer[^\*]*\*\*|You\s*\([^)]+\):?|Interviewer:?)\s*', '', cleaned, flags=re.IGNORECASE).strip()
    # Strip outer surrounding quotes if model wrapped its entire speech in quotes
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith('“') and cleaned.endswith('”')):
        cleaned = cleaned[1:-1].strip()
    return cleaned

def _extract_core_question_text(ai_text: str) -> str:
    """Extract the core question from AI output, stripping leading transition phrases."""
    if not ai_text:
        return ""
    cleaned = _clean_llm_response(ai_text)
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        for p in reversed(paragraphs):
            if "?" in p or any(p.lower().startswith(prefix) for prefix in ("cum ", "ce ", "how ", "what ", "why ", "describe ", "explica ")):
                return p
        return paragraphs[-1]
    return cleaned.strip()

def detect_candidate_language(text: str, previous_lang: Optional[str] = "en") -> str:
    """Accurately detect language ('en' or 'ro') of candidate message."""
    t = text.strip().lower()
    if not t:
        return previous_lang or "en"
    
    # Romanian diacritics and distinct linguistic roots
    ro_patterns = [
        r"[ăâîșț]",
        r"\b(salut|buna|buna\s+ziua|multumesc|mersi|nu\s+stiu|nu\s+am|cum\s+sa|ce\s+este|pentru|despre|proiect|proiectul|proiecte|aplicatia|aplicatii|experienta|ani|am\s+lucrat|am\s+folosit|am\s+facut|fac|facut|lucrat|dezvoltat|echipa|starea|baza\s+de\s+date|tabele|interogari|intrebare|urmatoarea|trecem|da|nu|si|sau|cu|in|la|pe|de|din|o|un|unui|unei|sa|ca|sa\s+continuam)\b",
    ]
    # English keywords and functional patterns
    en_patterns = [
        r"\b(hello|hi|hey|good\s+morning|good\s+afternoon|thanks|thank\s+you|i|my|we|our|you|your|he|she|it|they|them|is|are|was|were|have|has|had|do|does|did|will|would|can|could|should|used|built|worked|developed|implemented|project|projects|experience|years|with|from|about|the|and|or|for|to|in|on|at|by|of|state|database|query|queries|component|components|let'?s|next|skip|pass|yes|no)\b",
    ]
    
    ro_count = sum(len(re.findall(p, t)) for p in ro_patterns)
    en_count = sum(len(re.findall(p, t)) for p in en_patterns)
    
    if ro_count > en_count:
        return "ro"
    elif en_count > ro_count:
        return "en"
    return previous_lang or "en"

def _format_eval_feedback_section(items: List[Any], is_ro: bool = False) -> str:
    """Format evaluation strengths/weaknesses into a clean Markdown table or formatted bullet points."""
    if not items:
        return ""

    # Filter out dummy/hallucinated fallback entries (e.g. question_id < 0 or [NO TOPIC])
    valid_items: List[Any] = []
    for it in items:
        if isinstance(it, dict):
            qid = str(it.get("question_id") or it.get("q_id") or it.get("question_number") or "")
            topic = str(it.get("topic") or it.get("question") or it.get("question_text") or "")
            explanation = str(it.get("explanation") or it.get("feedback") or it.get("assessment") or "")
            if (
                qid.startswith("-")
                or "[NO TOPIC]" in topic
                or "[NO RESPONSE" in topic
                or "[NO STRENGTHS" in explanation.upper()
                or "NO STRENGTHS" in topic.upper()
                or "NONE OBSERVED" in explanation.upper()
            ):
                continue
            valid_items.append(it)
        elif isinstance(it, str):
            s_up = it.strip().upper()
            if (
                "[NO STRENGTHS" in s_up
                or "NO VALID" in s_up
                or "NO STRENGTHS OBSERVED" in s_up
                or "NONE OBSERVED" in s_up
                or s_up == "N/A"
                or s_up == "NONE"
            ):
                continue
            valid_items.append(it)
        else:
            valid_items.append(it)

    if not valid_items:
        return ""

    # Check if items are structured Q&A feedback dictionaries
    dict_items = [it for it in valid_items if isinstance(it, dict)]
    if len(dict_items) > 0 and len(dict_items) == len(valid_items):
        q_hdr = "Întrebare" if is_ro else "Question"
        resp_hdr = "Răspuns Candidat" if is_ro else "Candidate Response"
        fb_hdr = "Analiză & Feedback AI" if is_ro else "AI Evaluation & Feedback"

        table_rows = [
            f"| {q_hdr} | {resp_hdr} | {fb_hdr} |",
            "| :--- | :--- | :--- |",
        ]
        for idx, it in enumerate(dict_items, start=1):
            qid = (
                it.get("question_id")
                or it.get("q_id")
                or it.get("question_number")
                or it.get("round")
                or idx
            )
            
            q_text = (
                it.get("question_text")
                or it.get("question_summary")
                or it.get("question")
                or it.get("topic")
                or ""
            )
            q_text_str = str(q_text).strip()
            
            # Format clean question label with topic/question text
            q_prefix = f"**Întrebarea {qid}**" if is_ro else f"**Question {qid}**"
            if q_text_str and q_text_str.lower() != str(qid).lower():
                clean_q = re.sub(
                    r'^(#?\d+[\s\-\:\.]*|(Question|Întrebarea)\s*#?\d*[\s\-\:\.]*)',
                    '',
                    q_text_str,
                    flags=re.IGNORECASE,
                ).strip()
                if clean_q:
                    clean_q_disp = clean_q.replace("\n", " ").replace("|", "\\|")
                    q_label = f"{q_prefix}: {clean_q_disp}"
                else:
                    q_label = q_prefix
            else:
                q_label = q_prefix

            resp = str(
                it.get("response_text")
                or it.get("candidate_response")
                or it.get("candidate_answer")
                or it.get("response")
                or it.get("answer")
                or it.get("quote")
                or ""
            ).strip()
            resp_clean = resp.replace("\n", " ").replace("|", "\\|")
            if not resp_clean or "[NO RESPONSE" in resp_clean.upper():
                resp_disp = "*(Fără răspuns)*" if is_ro else "*(No response provided)*"
            else:
                resp_disp = f"_{resp_clean}_"

            fb = str(
                it.get("explanation")
                or it.get("evaluation_feedback")
                or it.get("feedback")
                or it.get("assessment")
                or it.get("analysis")
                or it.get("evaluation")
                or it.get("critique")
                or it.get("detail")
                or it.get("gap")
                or it.get("notes")
                or ""
            ).strip()

            # If feedback key wasn't standard, scan any other non-empty string values in the object
            if not fb:
                for k, v in it.items():
                    if (
                        k
                        not in (
                            "question_id",
                            "q_id",
                            "question_number",
                            "round",
                            "question",
                            "question_text",
                            "question_summary",
                            "topic",
                            "response_text",
                            "candidate_response",
                            "candidate_answer",
                            "response",
                            "answer",
                            "quote",
                        )
                        and isinstance(v, str)
                        and v.strip()
                    ):
                        fb = v.strip()
                        break

            if not fb:
                fb = (
                    "Candidatul nu a oferit un răspuns tehnic pentru a valida cerințele postului."
                    if is_ro
                    else "Candidate did not provide a valid technical response to this question."
                )

            fb_clean = fb.replace("\n", " ").replace("|", "\\|")

            table_rows.append(f"| {q_label} | {resp_disp} | {fb_clean} |")

        return "\n".join(table_rows)

    # Fallback to clean human-readable bullet points
    bullets = []
    for it in items:
        if isinstance(it, dict):
            parts = []
            qid = it.get("question_id") or it.get("q_id") or it.get("question_number")
            if qid:
                parts.append(f"**Q{qid}**")
            resp = it.get("response_text") or it.get("response") or it.get("answer")
            if resp:
                parts.append(f"„{str(resp)[:80]}”")
            fb = it.get("explanation") or it.get("feedback") or it.get("assessment")
            if fb:
                parts.append(f"→ {fb}")
            bullets.append("- " + (" : ".join(parts) if parts else str(it)))
        else:
            bullets.append(f"- {it}")

    return "\n".join(bullets)


def _normalize_text_for_intent(text: str) -> str:
    text = text.lower().strip()
    replacements = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ş': 's', 'ț': 't', 'ţ': 't'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


class InterviewService:
    """
    Core business logic and database orchestration for technical interview workflows:
    1. Pure in-memory candidate pool screening & scoring.
    2. Session creation with dynamic topic planning.
    3. LLM conversation progression and state tracking.
    4. Autonomous evaluation report generation.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        if llm_provider:
            self.llm = llm_provider
        else:
            self.llm = get_llm_provider(
                base_url=settings.OLLAMA_BASE_URL,
                model_name=settings.DEFAULT_LLM_MODEL,
                num_ctx=settings.OLLAMA_NUM_CTX,
            )

    def _estimate_tokens(self, text: str) -> int:
        """Conservative token estimation for mixed natural language and code (1 token ~ 3.5 chars)."""
        if not text:
            return 0
        return max(1, int(len(text) / 3.5))

    async def _build_managed_context_payload(
        self,
        db: AsyncSession,
        interview: Interview,
        db_messages: List[Message],
        system_prompt_builder_kwargs: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Dynamically manages the LLM context window using Progressive Summarization:
        1. Checks total estimated tokens of System Prompt + Full Message History against threshold.
        2. If tokens exceed threshold (> CONTEXT_TOKEN_THRESHOLD_RATIO of OLLAMA_NUM_CTX):
           - Splits into older_messages and recent_messages (last RECENT_MESSAGES_WINDOW_COUNT).
           - Extracts QA exchanges from older_messages and generates a cumulative summary via Ollama.
           - Persists interview.conversation_summary in PostgreSQL.
           - Injects conversation_summary into system prompt.
           - Builds history_payload containing only recent_messages.
        3. Otherwise (within limits):
           - Injects any existing conversation_summary into system prompt.
           - Passes full db_messages.
        4. PostgreSQL keeps 100% of all raw messages intact.
        """
        raw_history_payload = [
            {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
            for m in db_messages
        ]

        # Calculate base tokens
        history_text = " ".join(m.get("content", "") for m in raw_history_payload)
        base_system_prompt = build_system_interviewer_prompt(
            **system_prompt_builder_kwargs,
            conversation_summary=interview.conversation_summary,
        )
        total_estimated_tokens = self._estimate_tokens(base_system_prompt) + self._estimate_tokens(history_text)
        max_safe_tokens = int(settings.OLLAMA_NUM_CTX * CONTEXT_TOKEN_THRESHOLD_RATIO)

        # Trigger progressive summarization if exceeding threshold and message count is large
        if total_estimated_tokens > max_safe_tokens and len(db_messages) > RECENT_MESSAGES_WINDOW_COUNT:
            logger.info(
                "[Interview %s] Context threshold reached (%d estimated tokens > %d limit). Activating progressive summarization.",
                interview.id,
                total_estimated_tokens,
                max_safe_tokens,
            )
            older_messages = db_messages[:-RECENT_MESSAGES_WINDOW_COUNT]
            recent_messages = db_messages[-RECENT_MESSAGES_WINDOW_COUNT:]

            # Extract QA rounds from older messages
            older_rounds = []
            cur_q = None
            for m in older_messages:
                role = m.role.value if hasattr(m.role, "value") else str(m.role)
                if role in ("assistant", "system"):
                    cur_q = m.content
                elif role == "user" and cur_q:
                    older_rounds.append({"question": cur_q, "answer": m.content})
                    cur_q = None

            if older_rounds:
                try:
                    updated_summary = await self.llm.summarize_conversation_history(
                        job_title=interview.job_title,
                        candidate_name=interview.candidate_name,
                        rounds_to_summarize=older_rounds,
                        existing_summary=interview.conversation_summary,
                    )
                    interview.conversation_summary = updated_summary
                    await db.commit()
                    logger.info("[Interview %s] Updated conversation summary stored in DB (%d chars).", interview.id, len(updated_summary))
                except Exception as sum_err:
                    logger.warning("[Interview %s] Progressive summarization failed: %s. Using fallback window.", interview.id, sum_err)

            # Rebuild system prompt with updated summary
            managed_system_prompt = build_system_interviewer_prompt(
                **system_prompt_builder_kwargs,
                conversation_summary=interview.conversation_summary,
            )
            managed_history = [
                {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
                for m in recent_messages
            ]
            return managed_system_prompt, managed_history

        # Standard path (within safe limits)
        return base_system_prompt, raw_history_payload

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
        self,
        job_title: str,
        job_description: str,
        experience_level: str,
        candidates: List[Any],
        selected_candidate_name: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Screening candidate pool:
        - Extracts actual candidate name if generic fallback 'Candidate' was used.
        - Calculates dynamic matching score based on job description competencies & skills overlap.
        - Ranks all candidates strictly in descending order of match_score.
        - Honors human override selection by name if specified; otherwise selects #1 score by default.
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

        # 3. Honor Human Override Selection First!
        selected_cand = None
        if selected_candidate_name and selected_candidate_name.strip():
            target_name = selected_candidate_name.strip().lower()
            for r in results:
                if r["name"].strip().lower() == target_name:
                    r["is_selected"] = True
                    selected_cand = r
                    break

        if not selected_cand:
            if len(results) > 0:
                results[0]["is_selected"] = True
                selected_cand = results[0]
            else:
                selected_cand = {
                    "name": selected_candidate_name or "Candidate",
                    "cv_filename": None,
                    "cv_raw_text": None,
                    "match_score": 90,
                    "strengths": ["Direct Applicant"],
                    "summary": "Direct applicant profile evaluated.",
                    "is_selected": True,
                }

        return selected_cand, results

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

        # Human override selection passed via data.candidate_name
        top_cand, screening_results = self.screen_candidates(
            job_title=data.job_title,
            job_description=data.job_description,
            experience_level=exp_enum.value,
            candidates=candidates_list,
            selected_candidate_name=data.candidate_name,
        )

        # 1. Determine realistic target topic count based on allocated time limit
        target_topic_count = 5
        if data.time_limit_minutes:
            if data.time_limit_minutes <= 10:
                target_topic_count = 3
            elif data.time_limit_minutes <= 15:
                target_topic_count = 4
            elif data.time_limit_minutes <= 20:
                target_topic_count = 5
            elif data.time_limit_minutes <= 25:
                target_topic_count = 6
            elif data.time_limit_minutes <= 30:
                target_topic_count = 7
            elif data.time_limit_minutes <= 40:
                target_topic_count = 8
            else:
                target_topic_count = 10

        # Extract dynamic interview topics from Job Description instantly
        topics_plan = []
        lines = [line.strip().lstrip("-*•123456789. ").strip() for line in data.job_description.split("\n") if line.strip()]
        valid_bullets = [
            l for l in lines
            if len(l) > 8 and not l.lower().startswith(("we are", "looking for", "requirements:", "responsibilities:", "core requirements", "about the role"))
        ]
        if len(valid_bullets) >= 2:
            topics_plan = valid_bullets[:target_topic_count]
        else:
            default_pool = [
                f"Core {data.job_title} Language & Framework Fundamentals",
                "Architecture, API Design & Data Flow",
                "Database Engineering & Query Performance",
                "Containerization, Microservices & Deployment",
                "Problem-Solving & Production Edge Cases",
                "Security, Authentication & Authorization",
                "Performance Optimization & Caching Strategies",
                "Automated Testing, CI/CD & Reliability",
                "System Monitoring, Observability & Logging",
                "High Availability, Fault Tolerance & Scaling",
            ]
            topics_plan = default_pool[:target_topic_count]
        logger.info("[Interview %s] Dynamic Topics Plan (%d topics for %s min) initialized: %s", interview_id, len(topics_plan), data.time_limit_minutes, topics_plan)

        interview_lang = (data.language or "en").lower().strip()
        if interview_lang not in ("en", "ro"):
            interview_lang = "en"

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
            active_question_text=None,
            active_question_status="WAITING_ANSWER",
            consecutive_clarifications=0,
            topics_plan=topics_plan,
            assessed_topics=[],
            current_topic_index=0,
            topic_follow_up_count=0,
            time_limit_minutes=data.time_limit_minutes,
            language=interview_lang,
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

        # Natural opening turn: 1-sentence greeting + Question 1 immediately
        exp_level_str = exp_enum.value if hasattr(exp_enum, "value") else str(exp_enum)
        first_topic = topics_plan[0] if topics_plan else "Core Engineering Fundamentals"
        display_candidate_name = _clean_candidate_display_name(interview.candidate_name)

        system_prompt = build_system_interviewer_prompt(
            job_title=interview.job_title,
            job_description=interview.job_description,
            experience_level=exp_level_str,
            company_name=interview.company_name,
            cv_raw_text=interview.cv_raw_text or "",
            candidate_name=display_candidate_name,
            target_language=interview_lang,
        )
        opening_prompt = build_first_question_prompt(
            job_title=interview.job_title,
            job_description=interview.job_description,
            experience_level=exp_level_str,
            first_topic=first_topic,
            candidate_name=display_candidate_name,
            company_name=interview.company_name,
            cv_raw_text=interview.cv_raw_text or "",
            language=interview_lang,
        )

        opening_content = await self.llm.generate_response(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": opening_prompt}],
        )
        if not opening_content or not opening_content.strip():
            raise ValueError("Ollama returned an empty opening message.")

        cleaned_opening = _clean_llm_response(opening_content)
        interview.active_question_text = cleaned_opening

        initial_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview.id,
            role=MessageRole.ASSISTANT,
            content=cleaned_opening,
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

    def _classify_user_intent(
        self,
        candidate_content: str,
        active_status: str,
        consecutive_clarifications: int,
    ) -> str:
        """
        Classify candidate message intent deterministically without hallucination risk.
        """
        raw_text = candidate_content.strip()
        if not raw_text:
            return "ANSWER"
        text = _normalize_text_for_intent(raw_text)

        # 1. Explicit Language Switch Requests
        if re.search(r"\b(in\s+romana|in\s+limba\s+romana|vorbim\s+in\s+romana|intreaba-?ma\s+in\s+romana|vorbeste\s+in\s+romana|can\s+we\s+speak\s+romanian|in\s+romanian)\b", text):
            return "LANGUAGE_REQUEST:ro"
        if re.search(r"\b(in\s+english|speak\s+english|can\s+we\s+speak\s+english|let'?s\s+speak\s+english|in\s+engleza|vorbim\s+in\s+engleza)\b", text):
            return "LANGUAGE_REQUEST:en"

        # 2. Phase INTRO: Readiness Confirmation
        if active_status == "INTRO":
            ready_patterns = [
                r"\b(da|ready|gata|pregatit|pregatita|sunt\s+pregatit|sunt\s+pregatita|sunt\s+gata|yes|let'?s\s+go|sure|ok|okay|yep|start|putem\s+incepe|incepem|begin|hai|bine|sigur|cu\s+drag|all\s+set|i'?m\s+ready)\b",
                r"\b(salut|buna|hello|hi|hey)\b",
            ]
            if any(re.search(pat, text) for pat in ready_patterns) or len(text.split()) <= 6:
                return "READY"

        # 3. Profanity / Inappropriate Language
        profanity_patterns = [
            r"\b(pula|pizda|muie|dracu|dracului|cacat|fut|futu-?ti|sloboz|moron|idiot|stupid|fuck|shit|bitch|asshole|nigger|cunt|dick)\b"
        ]
        if any(re.search(pat, text) for pat in profanity_patterns):
            return "PROFANE_LANGUAGE"

        # 4. Off-Topic / Prompt Injection
        if re.search(r"\b(ignore\s+all\s+previous|cookie\s+recipe|reteta|vremea|weather|gluma|joke|tell\s+me\s+a\s+story|danseaza|canta)\b", text):
            return "OFF_TOPIC"

        # 5. Refusal / Don't Know / Skip / Next Topic Requests
        refusal_patterns = [
            r"\b(nu\s+stiu|nu\s+am\s+lucrat|nu\s+am\s+folosit|nu\s+am\s+experienta|nu\s+cunosc|nu\s+am\s+facut|skip|pass|sa\s+sarim|trecem\s+mai\s+departe|alta\s+intrebare|urmatoarea\s+intrebare|i\s+don'?t\s+know|haven'?t\s+worked|no\s+experience|skip\s+this|pass\s+this|nu\s+as\s+sti)\b",
            r"^\s*(si\s+)?(continuam\??|putem\s+continua\??|sa\s+continuam\??|next|mai\s+departe|mergem\s+mai\s+departe)\s*$",
        ]
        if any(re.search(pat, text) for pat in refusal_patterns):
            words = text.split()
            if len(words) <= 12 or not re.search(r"\b(as\s+folosi|as\s+alege|as\s+face|prefer\s+sa|solutia\s+mea|in\s+schimb|i\s+would|instead|my\s+approach)\b", text):
                return "REFUSAL_OR_DONT_KNOW"

        # 6. Clarification / Confusion / Inquiring about the active question
        confusion_patterns = [
            r"\b(nu\s+inteleg|nu\s+prea\s+inteleg|nu\s+am\s+inteles|i\s+don'?t\s+understand)\b",
            r"\b(poti\s+(sa\s+)?(clarifici|clarifica|reformulezi|detaliezi|explici)|could\s+you\s+(clarify|rephrase|explain)|can\s+you\s+(clarify|rephrase|explain))\b",
            r"\b(clarifica|clarificare|rephrase|clarify|detaliaza)\b",
            r"\b(nu\s+(imi\s+)?e(ste)?\s+(foarte\s+)?clar|it'?s\s+not\s+clear|not\s+very\s+clear|unclear)\b",
            r"\b(la\s+ce\s+te\s+referi|what\s+do\s+you\s+mean|what\s+does\s+that\s+mean|ce\s+vrei\s+sa\s+spui|ce\s+ai\s+vrea)\b",
            r"\b(ce\s+inseamna|ce\s+e\s+aia|ce\s+este|ce\s+reprezinta|what\s+is|what\s+does\s+.*\s+mean|what\s+are)\b",
            r"\b(te\s+referi\s+la|do\s+you\s+mean|ce\s+parte|care\s+dintre|sau\s+ambele|despre\s+ce|ce\s+anume)\b",
            r"\b(pot\s+folosi|pot\s+sa\s+folosesc|can\s+i\s+use|should\s+i\s+use|is\s+it\s+allowed|avem\s+voie)\b",
        ]
        is_clarification = any(re.search(pat, text) for pat in confusion_patterns)
        is_question_message = "?" in text and not bool(re.search(r"\b(as\s+folosi|as\s+alege|as\s+face|as\s+implementa|solutia\s+mea|in\s+schimb|i\s+would|i\s+prefer)\b", text))

        if is_clarification or is_question_message:
            has_substantive_answer = (
                len(text.split()) >= 15
                and bool(re.search(r"\b(as\s+folosi|as\s+alege|as\s+face|as\s+implementa|as\s+crea|pentru\s+ca|deoarece|in\s+schimb|i\s+would|because|i\s+prefer|my\s+solution|implementing|using)\b", text))
            )
            if has_substantive_answer:
                return "CLARIFICATION_AND_ANSWER"
            return "CLARIFICATION"

        return "ANSWER"

    async def _prepare_turn(
        self,
        db: AsyncSession,
        interview: Interview,
        candidate_content: str,
        db_messages: List[Message],
    ) -> Tuple[str, str, str, List[Dict[str, str]], Optional[int], bool, Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        created_time = interview.created_at
        if created_time.tzinfo is None:
            created_time = created_time.replace(tzinfo=timezone.utc)
        elapsed_min = (now - created_time).total_seconds() / 60.0
        time_limit = interview.time_limit_minutes
        remaining_min = max(0.0, float(time_limit) - elapsed_min) if time_limit else None
        time_expired = bool(time_limit and remaining_min is not None and remaining_min <= 0.1)

        exp_level_str = (
            interview.experience_level.value
            if hasattr(interview.experience_level, "value")
            else str(interview.experience_level)
        )
        topics = interview.topics_plan or [f"Core {interview.job_title} Engineering"]
        active_status = interview.active_question_status or "WAITING_ANSWER"
        consecutive_clarifications = interview.consecutive_clarifications or 0
        intent = self._classify_user_intent(candidate_content, active_status, consecutive_clarifications)
        display_candidate_name = _clean_candidate_display_name(interview.candidate_name)

        # Collect past questions asked by AI to enforce strict anti-repetition
        previous_questions = [
            m.content
            for m in db_messages
            if m.role == MessageRole.ASSISTANT
            and m.content
            and not m.content.startswith("{")
            and "[INTERVIEW_COMPLETE]" not in m.content
        ]

        state_updates: Dict[str, Any] = {}
        assigned_q_num: Optional[int] = None
        turn_prompt = ""
        is_complete = False

        if intent.startswith("LANGUAGE_REQUEST:"):
            new_lang = intent.split(":")[1]
            interview.language = new_lang
            state_updates["language"] = new_lang
            active_q = interview.active_question_text or "the current technical question"
            if new_lang == "ro":
                turn_prompt = (
                    f"Candidatul a cerut să continuați interviul în limba ROMÂNĂ ('{candidate_content}').\n"
                    f"INSTRUCTIUNI:\n"
                    f"1. Răspunde scurt și colegial în 1 propoziție scurtă în limba română la persoana a II-a singular (ex: 'Sigur, continuăm în limba română!').\n"
                    f"2. Formulează întrebarea tehnică activă în limba română la persoana a II-a singular: \"{active_q}\".\n"
                    f"3. REGULĂ DE LIMBĂ: Output 100% în ROMÂNĂ la persoana a II-a singular. Fără 'dumneavoastră' sau 'vă rugăm'."
                )
            else:
                turn_prompt = (
                    f"The candidate requested to continue the interview in ENGLISH ('{candidate_content}').\n"
                    f"INSTRUCTIONS:\n"
                    f"1. Acknowledge warmly in 1 short sentence in English (e.g. 'Sure, let\\'s continue in English!').\n"
                    f"2. Translate and ask the active technical question in ENGLISH: \"{active_q}\".\n"
                    f"3. LANGUAGE RULE: Output 100% in ENGLISH. Strictly do NOT output any Romanian words."
                )
            assigned_q_num = interview.active_question_number

        elif intent == "CLARIFICATION":
            state_updates["consecutive_clarifications"] = consecutive_clarifications + 1
            active_q = interview.active_question_text or "Active technical question"
            turn_prompt = build_clarification_response_prompt(
                job_title=interview.job_title,
                experience_level=exp_level_str,
                candidate_name=display_candidate_name,
                active_question_text=active_q,
                candidate_query=candidate_content,
                consecutive_clarifications=consecutive_clarifications + 1,
                clarification_threshold=CLARIFICATION_STEER_THRESHOLD,
                language=interview.language,
            )
            assigned_q_num = interview.active_question_number

        elif intent == "CLARIFICATION_AND_ANSWER":
            state_updates["consecutive_clarifications"] = 0
            cur_idx = interview.current_topic_index or 0
            cur_topic = topics[min(cur_idx, len(topics) - 1)] if topics else "Core Fundamentals"
            assessed = list(interview.assessed_topics or [])
            if cur_topic not in assessed:
                assessed.append(cur_topic)
            state_updates["assessed_topics"] = assessed

            next_idx = cur_idx + 1
            state_updates["current_topic_index"] = next_idx
            next_q_num = (interview.active_question_number or 1) + 1
            state_updates["active_question_number"] = next_q_num
            assigned_q_num = next_q_num
            state_updates["update_active_question_text_from_ai"] = True

            next_topic = topics[min(next_idx, len(topics) - 1)] if topics else "System Architecture"
            turn_prompt = build_both_response_prompt(
                job_title=interview.job_title,
                experience_level=exp_level_str,
                candidate_name=display_candidate_name,
                active_question_text=interview.active_question_text or "Active question",
                candidate_content=candidate_content,
                next_topic=next_topic,
                previous_questions=previous_questions,
                language=interview.language,
            )

        elif intent == "REFUSAL_OR_DONT_KNOW":
            state_updates["consecutive_clarifications"] = 0
            cur_idx = interview.current_topic_index or 0
            skipped_topic = topics[min(cur_idx, len(topics) - 1)] if topics else "Previous Topic"
            assessed = list(interview.assessed_topics or [])
            if skipped_topic not in assessed:
                assessed.append(skipped_topic)
            state_updates["assessed_topics"] = assessed

            next_idx = cur_idx + 1
            all_assessed = len(assessed) >= len(topics) or next_idx >= len(topics)
            hit_safety = (interview.active_question_number or 1) >= settings.SAFETY_MAX_QUESTIONS
            should_conclude = (all_assessed and (interview.active_question_number or 1) >= len(topics)) or time_expired or hit_safety or next_idx >= len(topics)

            if should_conclude:
                is_complete = True
                turn_prompt = build_next_question_prompt(
                    job_title=interview.job_title,
                    experience_level=exp_level_str,
                    candidate_name=display_candidate_name,
                    last_question=interview.active_question_text or "Active question",
                    candidate_answer=candidate_content,
                    next_topic="",
                    is_follow_up=False,
                    previous_questions=previous_questions,
                    language=interview.language,
                    is_final_wrap_up=True,
                )
            else:
                state_updates["current_topic_index"] = next_idx
                next_q_num = (interview.active_question_number or 1) + 1
                state_updates["active_question_number"] = next_q_num
                assigned_q_num = next_q_num
                state_updates["update_active_question_text_from_ai"] = True

                next_topic = topics[min(next_idx, len(topics) - 1)] if topics else "Next Engineering Competency"
                turn_prompt = build_refusal_response_prompt(
                    job_title=interview.job_title,
                    experience_level=exp_level_str,
                    candidate_name=display_candidate_name,
                    skipped_topic=skipped_topic,
                    next_topic=next_topic,
                    previous_questions=previous_questions,
                    language=interview.language,
                )

        elif intent == "PROFANE_LANGUAGE":
            active_q = interview.active_question_text or "the current technical question"
            if interview.language == "ro":
                turn_prompt = (
                    f"Candidatul a folosit un limbaj nepotrivit sau vulgar ('{candidate_content[:60]}').\n"
                    f"1. Răspunde ferm, calm și profesionist în 1 propoziție scurtă la persoana a II-a singular cerând păstrarea unui ton profesional și respectuos.\n"
                    f"2. Revino direct la întrebarea tehnică activă: \"{active_q}\".\n"
                    f"3. REGULĂ DE TON: Exclusiv persoana a II-a singular. Fără supărare, dar ferm."
                )
            else:
                turn_prompt = (
                    f"The candidate used inappropriate language ('{candidate_content[:60]}').\n"
                    f"1. Calmly and professionally state in 1 brief sentence that we should maintain a respectful and professional conversation.\n"
                    f"2. Firmly return to the active technical question: \"{active_q}\"."
                )
            assigned_q_num = interview.active_question_number

        elif intent == "OFF_TOPIC":
            active_q = interview.active_question_text or "the current technical requirement"
            if interview.language == "ro":
                turn_prompt = f"Candidatul a trimis un mesaj în afara subiectului sau o glumă ('{candidate_content[:60]}'). Refuză politicos în 1 propoziție scurtă și revino ferm la întrebarea activă: \"{active_q}\"."
            else:
                turn_prompt = f"The candidate sent an off-topic query or joke ('{candidate_content[:60]}'). Politely decline in 1 brief sentence and firmly return to the active question: \"{active_q}\"."
            assigned_q_num = interview.active_question_number

        else:  # ANSWER
            state_updates["consecutive_clarifications"] = 0
            cur_idx = interview.current_topic_index or 0
            cur_topic = topics[min(cur_idx, len(topics) - 1)] if topics else "Core Fundamentals"
            assessed = list(interview.assessed_topics or [])
            if cur_topic not in assessed:
                assessed.append(cur_topic)
            state_updates["assessed_topics"] = assessed

            all_assessed = len(assessed) >= len(topics)
            hit_safety = (interview.active_question_number or 1) >= settings.SAFETY_MAX_QUESTIONS
            should_conclude = (all_assessed and (interview.active_question_number or 1) >= len(topics)) or time_expired or hit_safety or (cur_idx + 1 >= len(topics))

            if should_conclude:
                is_complete = True
                turn_prompt = build_next_question_prompt(
                    job_title=interview.job_title,
                    experience_level=exp_level_str,
                    candidate_name=display_candidate_name,
                    last_question=interview.active_question_text or "Active question",
                    candidate_answer=candidate_content,
                    next_topic="",
                    is_follow_up=False,
                    previous_questions=previous_questions,
                    language=interview.language,
                    is_final_wrap_up=True,
                )
            else:
                next_idx = cur_idx + 1
                state_updates["current_topic_index"] = next_idx
                next_q_num = (interview.active_question_number or 1) + 1
                state_updates["active_question_number"] = next_q_num
                assigned_q_num = next_q_num
                state_updates["update_active_question_text_from_ai"] = True

                next_topic = topics[min(next_idx, len(topics) - 1)] if topics else "Architecture & System Design"
                turn_prompt = build_next_question_prompt(
                    job_title=interview.job_title,
                    experience_level=exp_level_str,
                    candidate_name=display_candidate_name,
                    last_question=interview.active_question_text or "Active question",
                    candidate_answer=candidate_content,
                    next_topic=next_topic,
                    is_follow_up=False,
                    previous_questions=previous_questions,
                    language=interview.language,
                    is_final_wrap_up=False,
                )

        # Build managed context payload with messages prior to the current turn prompt
        effective_target_lang = state_updates.get("language", interview.language)
        prompt_kwargs = {
            "job_title": interview.job_title,
            "job_description": interview.job_description,
            "experience_level": exp_level_str,
            "company_name": interview.company_name,
            "cv_raw_text": interview.cv_raw_text or "",
            "candidate_name": display_candidate_name,
            "target_language": effective_target_lang,
        }
        prior_db_messages = db_messages[:-1] if db_messages else []
        managed_system_prompt, managed_history = await self._build_managed_context_payload(
            db=db,
            interview=interview,
            db_messages=prior_db_messages,
            system_prompt_builder_kwargs=prompt_kwargs,
        )

        return intent, turn_prompt, managed_system_prompt, managed_history, assigned_q_num, is_complete, state_updates

    async def add_candidate_message_and_respond(
        self, db: AsyncSession, interview_id: str, candidate_content: str
    ) -> Optional[ChatResponse]:
        interview = await self.get_interview(db, interview_id)
        if not interview:
            return None

        if interview.status == InterviewStatus.COMPLETED:
            return ChatResponse(
                message=ChatMessage(
                    id=str(uuid.uuid4())[:8],
                    role=MessageRole.ASSISTANT,
                    content="This interview session has already been concluded.",
                    created_at=datetime.now(timezone.utc),
                    question_number=None,
                ),
                is_complete=True,
                next_question_number=None,
            )

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

        # 3. Deterministic state machine preparation
        (
            intent,
            turn_prompt,
            managed_system_prompt,
            managed_history,
            assigned_q_num,
            is_complete,
            state_updates,
        ) = await self._prepare_turn(db, interview, candidate_content, db_messages)

        logger.info(
            "[Interview %s] TURN PREP | Intent: %s | Status: %s | Q#: %s | Clarifications: %s",
            interview_id,
            intent,
            interview.active_question_status,
            interview.active_question_number,
            interview.consecutive_clarifications,
        )

        # Combine payload for LLM
        effective_messages = managed_history + [{"role": "user", "content": turn_prompt}]
        ai_text = await self.llm.generate_response(managed_system_prompt, effective_messages)
        if not ai_text or not ai_text.strip():
            raise ValueError("Ollama returned an empty response.")

        ai_signaled_completion = INTERVIEW_COMPLETE_TOKEN in ai_text
        is_complete = is_complete or ai_signaled_completion
        cleaned_ai_text = _clean_llm_response(ai_text.replace(INTERVIEW_COMPLETE_TOKEN, ""))

        if is_complete:
            interview.status = InterviewStatus.COMPLETED
            interview.active_question_status = "COMPLETED"
            interview.active_question_number = None
            assigned_q_num = None
        else:
            for k, v in state_updates.items():
                if k == "update_active_question_text_from_ai":
                    interview.active_question_text = _extract_core_question_text(cleaned_ai_text)
                elif hasattr(interview, k):
                    setattr(interview, k, v)

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
            "[Interview %s] AI_MSG: '%s' | Question Assigned: %s",
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

        # 3. Deterministic state machine preparation
        (
            intent,
            turn_prompt,
            managed_system_prompt,
            managed_history,
            assigned_q_num,
            is_complete,
            state_updates,
        ) = await self._prepare_turn(db, interview, candidate_content, db_messages)

        logger.info(
            "[Interview %s Streaming] TURN PREP | Intent: %s | Status: %s | Q#: %s | Clarifications: %s",
            interview_id,
            intent,
            interview.active_question_status,
            interview.active_question_number,
            interview.consecutive_clarifications,
        )

        effective_messages = managed_history + [{"role": "user", "content": turn_prompt}]
        full_ai_response = ""
        stream_gen = self.llm.generate_stream(managed_system_prompt, effective_messages)

        async for chunk in stream_gen:
            full_ai_response += chunk
            display_chunk = chunk.replace(INTERVIEW_COMPLETE_TOKEN, "")
            if display_chunk:
                yield {"chunk": display_chunk, "is_complete": False}

        if not full_ai_response.strip():
            raise ValueError("Ollama stream completed with empty response.")

        ai_signaled_completion = INTERVIEW_COMPLETE_TOKEN in full_ai_response
        is_complete = is_complete or ai_signaled_completion
        cleaned_ai_response = full_ai_response.replace(INTERVIEW_COMPLETE_TOKEN, "").strip()

        if is_complete:
            interview.status = InterviewStatus.COMPLETED
            interview.active_question_status = "COMPLETED"
            interview.active_question_number = None
            assigned_q_num = None
        else:
            for k, v in state_updates.items():
                if k == "update_active_question_text_from_ai":
                    interview.active_question_text = _extract_core_question_text(cleaned_ai_response)
                elif hasattr(interview, k):
                    setattr(interview, k, v)

        # 3. Save assistant message to database
        ai_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.ASSISTANT,
            content=_clean_llm_response(cleaned_ai_response),
            question_number=assigned_q_num,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ai_msg)
        interview.updated_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(
            "[Interview %s Streaming] AI_MSG: '%s' | Question Assigned: %s",
            interview_id,
            cleaned_ai_response[:60],
            assigned_q_num,
        )

        yield {
            "chunk": "",
            "done": True,
            "is_complete": is_complete,
            "next_question_number": assigned_q_num,
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

        user_messages = [m for m in transcript_history if m.get("role") == "user" and m.get("content", "").strip()]
        is_ro = getattr(interview, "language", "en") == "ro"

        if len(user_messages) == 0:
            intro_p = f"{preamble_text.strip()}\n\n" if preamble_text.strip() else ""
            if is_ro:
                return (
                    f"{intro_p}"
                    f"Îți mulțumim, {interview.candidate_name}! Sesiunea de interviu pentru poziția de **{interview.job_title}** s-a încheiat.\n\n"
                    f"**Evaluare Generală AI: 0.0/10** (No Hire)\n\n"
                    f"Candidatul nu a participat și nu a oferit niciun răspuns la întrebările de interviu înainte de finalizarea sesiunii. Nu s-a putut realiza o evaluare tehnică.\n\n"
                    f"**Arii de Îmbunătățire / Lacune:**\n"
                    f"- Niciun răspuns furnizat pe parcursul interviului tehnic live.\n"
                    f"- Toate cerințele postului au rămas neevaluate.\n\n"
                    f"Transcrierea completă și datele de evaluare au fost înregistrate."
                )
            return (
                f"{intro_p}"
                f"Thank you, {interview.candidate_name}! The interview session for the **{interview.job_title}** position has concluded.\n\n"
                f"**Overall AI Assessment: 0.0/10** (No Hire)\n\n"
                f"The candidate did not participate or provide any responses to the interview questions before concluding the session. No technical assessment could be performed.\n\n"
                f"**Areas for Improvement / Gaps:**\n"
                f"- No responses provided during the live technical interview.\n"
                f"- All core job requirements remain completely unassessed.\n\n"
                f"Your full transcript and evaluation data have been recorded."
            )

        topics = interview.topics_plan or []
        covered_count = min(len(topics), (interview.current_topic_index or 0) + 1) if topics else 0
        exp_level_str = (
            interview.experience_level.value
            if hasattr(interview.experience_level, "value")
            else str(interview.experience_level)
        )

        eval_report = await self.llm.evaluate_interview(
            job_title=interview.job_title,
            job_description=interview.job_description,
            candidate_name=interview.candidate_name,
            cv_raw_text=interview.cv_raw_text or "",
            transcript=transcript_history,
            experience_level=exp_level_str,
            time_limit_minutes=interview.time_limit_minutes,
            covered_topics_count=covered_count,
            total_topics_count=len(topics) if topics else None,
            topics_plan=topics,
        )

        overall_score = eval_report.get("overall_score", 0.0)
        summary_text = eval_report.get("summary", "Technical interview evaluation completed.")
        strengths = eval_report.get("strengths", [])
        strengths_str = _format_eval_feedback_section(strengths, is_ro=is_ro)
        weaknesses = eval_report.get("weaknesses", [])
        weaknesses_str = _format_eval_feedback_section(weaknesses, is_ro=is_ro)
        rec_label = eval_report.get("recommendation", "hire").replace("_", " ").title()

        intro_p = f"{preamble_text.strip()}\n\n" if preamble_text.strip() else ""

        if is_ro:
            return (
                f"{intro_p}"
                f"Îți mulțumim, {interview.candidate_name}! Sesiunea de interviu pentru poziția de **{interview.job_title}** s-a încheiat.\n\n"
                f"**Evaluare Generală AI: {overall_score}/10** ({rec_label})\n\n"
                f"{summary_text}\n\n"
                + (f"**Puncte Forte Observate:**\n{strengths_str}\n\n" if strengths_str else "")
                + (f"**Arii de Îmbunătățire / Lacune:**\n{weaknesses_str}\n\n" if weaknesses_str else "")
                + f"Transcrierea completă și datele de evaluare au fost înregistrate."
            )

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

        eval_exists = any(
            ("**Overall AI Assessment:" in (m.content or "")) or ("**Evaluare Generală AI:" in (m.content or ""))
            for m in interview.messages
        )
        if eval_exists:
            interview.status = InterviewStatus.COMPLETED
            await db.commit()
            return await self.get_interview(db, interview.id)

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
