import asyncio
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict, Tuple, AsyncGenerator
from sqlalchemy import select, delete, update
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
    parse_transcript_into_qa_rounds,
    is_wrapup_or_evaluation_message,
)
from llm.agent import interview_graph, InterviewState
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
    """Sanitize model output: remove thinking tags, speaker/persona prefixes, meta observations, and outer quotes."""
    if not text:
        return ""
    # Strip <think>...</think> blocks if reasoning model emits them
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
    # Strip roleplay speaker prefixes like **You (Role):**, **Interviewer:**, Interviewer:, You:, etc.
    cleaned = re.sub(r'^\s*(\*\*You[^\*]+\*\*|\*\*Interviewer[^\*]*\*\*|You\s*\([^)]+\):?|Interviewer:?)\s*', '', cleaned, flags=re.IGNORECASE).strip()
    # Strip meta-observations, explanations, and notes (e.g. "Observație: ...", "Notă: ...", "Note: ...")
    cleaned = re.sub(r'(?i)\n*(Observa[țt]ie|Not[ăa]|Note|Explica[țt]ie)\s*:[\s\S]*$', '', cleaned).strip()
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

def _format_eval_feedback_section(
    items: List[Any],
    is_ro: bool = False,
    qa_rounds_map: Optional[Dict[int, Dict[str, Any]]] = None,
) -> str:
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
            raw_qid = (
                it.get("question_id")
                or it.get("q_id")
                or it.get("question_number")
                or it.get("round")
            )
            num_qid: Optional[int] = None
            if raw_qid is not None:
                try:
                    match = re.search(r'\d+', str(raw_qid))
                    if match:
                        num_qid = int(match.group(0))
                except (ValueError, TypeError):
                    pass

            qid = num_qid if num_qid is not None else idx

            q_text = (
                it.get("question_text")
                or it.get("question_summary")
                or it.get("question")
                or it.get("topic")
                or ""
            )
            q_text_str = str(q_text).strip()

            # If question text is empty or just the question id, lookup from qa_rounds_map
            if (not q_text_str or q_text_str.lower() == str(qid).lower()) and qa_rounds_map and num_qid in qa_rounds_map:
                mapped_q = qa_rounds_map[num_qid].get("question", "").strip()
                if mapped_q:
                    first_line = mapped_q.split("\n")[0].strip()
                    q_text_str = first_line[:120]

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

            # If response is missing or marked as [NO RESPONSE], verify whether candidate answered in the transcript
            if (not resp or "[NO RESPONSE" in resp.upper()) and qa_rounds_map and num_qid in qa_rounds_map:
                real_ans = qa_rounds_map[num_qid].get("answer", "").strip()
                if real_ans and not ("[NO RESPONSE" in real_ans.upper()):
                    resp = real_ans

            resp_clean = resp.replace("\n", " ").replace("|", "\\|").strip()
            if not resp_clean or "[NO RESPONSE" in resp_clean.upper():
                if "BEFORE REACHING TOPIC" in resp_clean.upper() or "UNASSESSED" in resp_clean.upper():
                    resp_disp = "*(Neevaluat - Sesiune finalizată prematur)*" if is_ro else "*(Unassessed - Session Concluded Early)*"
                else:
                    resp_disp = "*(Fără răspuns)*" if is_ro else "*(No response provided)*"
            else:
                if len(resp_clean) > 130:
                    snippet = resp_clean[:127].rstrip() + "..."
                else:
                    snippet = resp_clean
                resp_disp = f"_{snippet}_"

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
    for idx, it in enumerate(items, start=1):
        if isinstance(it, dict):
            parts = []
            raw_qid = it.get("question_id") or it.get("q_id") or it.get("question_number")
            num_qid = None
            if raw_qid is not None:
                try:
                    m = re.search(r'\d+', str(raw_qid))
                    if m:
                        num_qid = int(m.group(0))
                except (ValueError, TypeError):
                    pass
            qid = num_qid if num_qid is not None else idx
            if qid:
                parts.append(f"**Q{qid}**")
            resp = it.get("response_text") or it.get("response") or it.get("answer")
            if (not resp or "[NO RESPONSE" in str(resp).upper()) and qa_rounds_map and num_qid in qa_rounds_map:
                real_ans = qa_rounds_map[num_qid].get("answer", "").strip()
                if real_ans and not ("[NO RESPONSE" in real_ans.upper()):
                    resp = real_ans
            if resp:
                resp_str = str(resp).replace("\n", " ").strip()
                if len(resp_str) > 80:
                    resp_str = resp_str[:77] + "..."
                parts.append(f"„{resp_str}”")
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
        self._eval_locks: Dict[str, asyncio.Lock] = {}
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
                    logger.error("[Interview %s] Progressive summarization failed: %s", interview.id, sum_err)
                    raise RuntimeError(
                        f"[Interview {interview.id}] Progressive summarization failed: {sum_err}"
                    ) from sum_err

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

        # 1. Determine realistic target topic count based on allocated time limit (+2 to each, 5 min = 3)
        target_topic_count = 9
        if data.time_limit_minutes:
            if data.time_limit_minutes <= 5:
                target_topic_count = 3
            elif data.time_limit_minutes <= 10:
                target_topic_count = 5
            elif data.time_limit_minutes <= 15:
                target_topic_count = 6
            elif data.time_limit_minutes <= 20:
                target_topic_count = 7
            elif data.time_limit_minutes <= 25:
                target_topic_count = 8
            elif data.time_limit_minutes <= 30:
                target_topic_count = 9
            elif data.time_limit_minutes <= 40:
                target_topic_count = 10
            else:
                target_topic_count = 12

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
                "Domain-Driven Design, Modular Boundaries & Tech Debt",
                "Concurrency, Asynchronous Messaging & Real-World Tradeoffs",
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
            cand_id = res.get("id") or str(uuid.uuid4())[:8]
            cand_model = Candidate(
                id=cand_id,
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
        db_messages: Optional[List[Message]] = None,
    ) -> Tuple[str, List[Dict[str, str]], str, str, bool, Optional[int], Dict[str, Any]]:
        if db_messages is None:
            db_messages = list(interview.messages)
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
        
        # Prepare state for LangGraph workflow execution
        current_state: InterviewState = {
            "interview_id": interview.id,
            "job_title": interview.job_title,
            "company_name": interview.company_name,
            "job_description": interview.job_description,
            "experience_level": exp_level_str,
            "candidate_name": interview.candidate_name,
            "language": interview.language,
            "conversation_summary": interview.conversation_summary,
            "topics_plan": topics,
            "current_topic_index": interview.current_topic_index or 0,
            "assessed_topics": list(interview.assessed_topics or []),
            "topic_follow_up_count": interview.topic_follow_up_count or 0,
            "active_question_number": interview.active_question_number or 1,
            "active_question_text": interview.active_question_text,
            "active_question_status": active_status,
            "consecutive_clarifications": consecutive_clarifications,
            "time_limit_minutes": time_limit,
            "remaining_minutes": remaining_min,
            "time_expired": time_expired,
            "candidate_message": candidate_content,
            "previous_questions": [
                m.content
                for m in db_messages
                if m.role == MessageRole.ASSISTANT
                and m.content
                and not m.content.startswith("{")
                and "[INTERVIEW_COMPLETE]" not in m.content
            ],
        }

        # Invoke LangGraph StateGraph agent for this turn
        graph_output = interview_graph.invoke(current_state)

        intent = graph_output.get("intent", "ANSWER")
        is_complete = graph_output.get("is_complete", False)
        turn_prompt = graph_output.get("turn_prompt", "")
        assigned_q_num = graph_output.get("assigned_q_num") or interview.active_question_number

        state_updates: Dict[str, Any] = {}
        if "language" in graph_output and graph_output["language"] != interview.language:
            interview.language = graph_output["language"]
            state_updates["language"] = graph_output["language"]
        if "consecutive_clarifications" in graph_output:
            state_updates["consecutive_clarifications"] = graph_output["consecutive_clarifications"]
        if "current_topic_index" in graph_output and graph_output["current_topic_index"] != interview.current_topic_index:
            state_updates["current_topic_index"] = graph_output["current_topic_index"]
        if "assessed_topics" in graph_output:
            state_updates["assessed_topics"] = graph_output["assessed_topics"]
        if "topic_follow_up_count" in graph_output:
            state_updates["topic_follow_up_count"] = graph_output["topic_follow_up_count"]
        if "active_question_number" in graph_output and graph_output["active_question_number"] != interview.active_question_number:
            state_updates["active_question_number"] = graph_output["active_question_number"]
        if "active_question_status" in graph_output:
            state_updates["active_question_status"] = graph_output["active_question_status"]
        if intent in ("ANSWER", "REFUSAL", "CLARIFICATION_AND_ANSWER"):
            state_updates["update_active_question_text_from_ai"] = True

        # Build managed context payload with messages prior to the current turn prompt
        effective_target_lang = state_updates.get("language", interview.language)
        display_candidate_name = _clean_candidate_display_name(interview.candidate_name)
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

        return (
            managed_system_prompt,
            managed_history,
            turn_prompt,
            intent,
            is_complete,
            assigned_q_num,
            state_updates,
        )

    async def respond_to_candidate_message(
        self, db: AsyncSession, interview_id: str, candidate_content: str
    ) -> Optional[Interview]:
        """Process incoming candidate message, enforce turn progression, and return updated Interview model."""
        interview = await self.get_interview(db, interview_id)
        if not interview:
            return None

        (
            managed_system_prompt,
            managed_history,
            turn_prompt,
            intent,
            is_complete,
            assigned_q_num,
            state_updates,
        ) = await self._prepare_turn(db, interview, candidate_content)

        now = datetime.now(timezone.utc)

        # 1. Save candidate message
        cand_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.USER,
            content=candidate_content,
            question_number=interview.active_question_number,
            created_at=now,
        )
        db.add(cand_msg)

        # 2. Generate or set deterministic AI response
        if is_complete:
            is_ro = getattr(interview, "language", "en") == "ro"
            display_candidate_name = _clean_candidate_display_name(interview.candidate_name)
            if is_ro:
                cleaned_ai_text = (
                    f"Îți mulțumim pentru participare și pentru răspunsurile oferite, {display_candidate_name}! "
                    f"Sesiunea de interviu tehnic pentru poziția de **{interview.job_title}** s-a încheiat. "
                    f"Transcrierea a fost înregistrată."
                )
            else:
                cleaned_ai_text = (
                    f"Thank you for participating and sharing your responses, {display_candidate_name}! "
                    f"The technical interview session for the **{interview.job_title}** position has concluded. "
                    f"Your transcript has been recorded."
                )
        else:
            effective_messages = managed_history + [{"role": "user", "content": turn_prompt}]
            try:
                ai_text = await self.llm.generate_response(managed_system_prompt, effective_messages)
            except Exception as gen_err:
                logger.warning("[Interview %s] Error on initial generation: %s", interview_id, gen_err)
                ai_text = ""

            if not ai_text or not ai_text.strip():
                logger.warning("[Interview %s] Empty AI response. Retrying once after 500ms...", interview_id)
                await asyncio.sleep(0.5)
                try:
                    ai_text = await self.llm.generate_response(managed_system_prompt, effective_messages)
                except Exception as retry_err:
                    logger.error("[Interview %s] Error on retry generation: %s", interview_id, retry_err)
                    ai_text = ""

            if not ai_text or not ai_text.strip():
                raise RuntimeError(
                    f"[Interview {interview_id}] AI model returned empty response. "
                    "Ensure Ollama is running and model is responding."
                )

            ai_signaled_completion = INTERVIEW_COMPLETE_TOKEN in ai_text
            is_complete = is_complete or ai_signaled_completion
            if is_complete:
                is_ro = getattr(interview, "language", "en") == "ro"
                display_candidate_name = _clean_candidate_display_name(interview.candidate_name)
                if is_ro:
                    cleaned_ai_text = (
                        f"Îți mulțumim pentru participare și pentru răspunsurile oferite, {display_candidate_name}! "
                        f"Sesiunea de interviu tehnic pentru poziția de **{interview.job_title}** s-a încheiat. "
                        f"Transcrierea a fost înregistrată."
                    )
                else:
                    cleaned_ai_text = (
                        f"Thank you for participating and sharing your responses, {display_candidate_name}! "
                        f"The technical interview session for the **{interview.job_title}** position has concluded. "
                        f"Your transcript has been recorded."
                    )
            else:
                cleaned_ai_text = _clean_llm_response(ai_text)

        if is_complete:
            interview.status = InterviewStatus.FINISHING
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

        return await self.get_interview(db, interview_id)

    async def add_candidate_message_and_respond(
        self, db: AsyncSession, interview_id: str, candidate_content: str
    ) -> Optional[ChatResponse]:
        """Process incoming candidate message and return typed ChatResponse for REST endpoint."""
        updated = await self.respond_to_candidate_message(db, interview_id, candidate_content)
        if not updated or not updated.messages:
            return None
        last_msg = updated.messages[-1]
        return ChatResponse(
            message=ChatMessage(
                id=last_msg.id,
                role=last_msg.role,
                content=last_msg.content,
                created_at=last_msg.created_at,
                question_number=last_msg.question_number,
            ),
            is_complete=(updated.status in (InterviewStatus.FINISHING, InterviewStatus.COMPLETED)),
            next_question_number=updated.active_question_number,
        )

    async def stream_candidate_message_and_respond(
        self, db: AsyncSession, interview_id: str, candidate_content: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream assistant response turn using Ollama SSE while preserving strict turn-taking rules."""
        interview = await self.get_interview(db, interview_id)
        if not interview:
            return

        (
            managed_system_prompt,
            managed_history,
            turn_prompt,
            intent,
            is_complete,
            assigned_q_num,
            state_updates,
        ) = await self._prepare_turn(db, interview, candidate_content)

        # 1. Save candidate message to database
        cand_msg = Message(
            id=str(uuid.uuid4())[:8],
            interview_id=interview_id,
            role=MessageRole.USER,
            content=candidate_content,
            question_number=interview.active_question_number,
            created_at=datetime.now(timezone.utc),
        )
        db.add(cand_msg)
        await db.commit()

        # 2. Handle stream or deterministic completion
        if is_complete:
            is_ro = getattr(interview, "language", "en") == "ro"
            display_candidate_name = _clean_candidate_display_name(interview.candidate_name)
            if is_ro:
                hardcoded_closing = (
                    f"Îți mulțumim pentru participare și pentru răspunsurile oferite, {display_candidate_name}! "
                    f"Sesiunea de interviu tehnic pentru poziția de **{interview.job_title}** s-a încheiat. "
                    f"Transcrierea a fost înregistrată."
                )
            else:
                hardcoded_closing = (
                    f"Thank you for participating and sharing your responses, {display_candidate_name}! "
                    f"The technical interview session for the **{interview.job_title}** position has concluded. "
                    f"Your transcript has been recorded."
                )

            words = hardcoded_closing.split(" ")
            for i in range(0, len(words), 3):
                chunk_str = " ".join(words[i : i + 3]) + (" " if i + 3 < len(words) else "")
                yield {"chunk": chunk_str, "is_complete": False}
                await asyncio.sleep(0.04)

            cleaned_ai_response = hardcoded_closing
            full_ai_response = hardcoded_closing
        else:
            effective_messages = managed_history + [{"role": "user", "content": turn_prompt}]
            full_ai_response = ""
            stream_gen = self.llm.generate_stream(managed_system_prompt, effective_messages)

            try:
                async for chunk in stream_gen:
                    full_ai_response += chunk
                    display_chunk = chunk.replace(INTERVIEW_COMPLETE_TOKEN, "")
                    if display_chunk:
                        yield {"chunk": display_chunk, "is_complete": False}
            except Exception as stream_err:
                logger.warning("[Interview %s] Stream error on initial attempt: %s", interview_id, stream_err)

            # Auto-retry once if stream was empty
            if not full_ai_response.strip():
                logger.warning("[Interview %s] Empty AI stream. Retrying once after 500ms backoff...", interview_id)
                await asyncio.sleep(0.5)
                try:
                    retry_stream = self.llm.generate_stream(managed_system_prompt, effective_messages)
                    async for chunk in retry_stream:
                        full_ai_response += chunk
                        display_chunk = chunk.replace(INTERVIEW_COMPLETE_TOKEN, "")
                        if display_chunk:
                            yield {"chunk": display_chunk, "is_complete": False}
                except Exception as retry_err:
                    logger.error("[Interview %s] Stream error on retry: %s", interview_id, retry_err)
                    raise RuntimeError(
                        f"[Interview {interview_id}] Stream error on retry from AI model: {retry_err}"
                    ) from retry_err

            # Fail fast if still empty after retry
            if not full_ai_response.strip():
                raise RuntimeError(
                    f"[Interview {interview_id}] AI model returned empty stream response. "
                    "Ensure Ollama is running and model is responding."
                )

            ai_signaled_completion = INTERVIEW_COMPLETE_TOKEN in full_ai_response
            is_complete = is_complete or ai_signaled_completion
            if is_complete:
                is_ro = getattr(interview, "language", "en") == "ro"
                display_candidate_name = _clean_candidate_display_name(interview.candidate_name)
                if is_ro:
                    cleaned_ai_response = (
                        f"Îți mulțumim pentru participare și pentru răspunsurile oferite, {display_candidate_name}! "
                        f"Sesiunea de interviu tehnic pentru poziția de **{interview.job_title}** s-a încheiat. "
                        f"Transcrierea a fost înregistrată."
                    )
                else:
                    cleaned_ai_response = (
                        f"Thank you for participating and sharing your responses, {display_candidate_name}! "
                        f"The technical interview session for the **{interview.job_title}** position has concluded. "
                        f"Your transcript has been recorded."
                    )
            else:
                cleaned_ai_response = full_ai_response.replace(INTERVIEW_COMPLETE_TOKEN, "").strip()

        if is_complete:
            interview.status = InterviewStatus.FINISHING
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

        yield {
            "chunk": "",
            "done": True,
            "is_complete": is_complete,
            "next_question_number": interview.active_question_number,
            "message_id": ai_msg.id,
        }

    async def _generate_evaluation_closing(
        self, interview: Interview, preamble_text: str = ""
    ) -> str:
        """Evaluate full interview transcript and generate candidate closing message with scores."""
        transcript_history = [
            {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
            for m in interview.messages
            if not is_wrapup_or_evaluation_message(m.content or "")
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

        qa_rounds = parse_transcript_into_qa_rounds(transcript_history)
        qa_rounds_map: Dict[int, Dict[str, Any]] = {}
        for r in qa_rounds:
            qid_val = r.get("question_id")
            if qid_val is not None:
                try:
                    qa_rounds_map[int(qid_val)] = r
                except (ValueError, TypeError):
                    pass

        # Count substantive answers
        answered_rounds = [
            r for r in qa_rounds
            if r.get("answer") and not (
                "[NO RESPONSE" in r.get("answer", "").upper()
                or r.get("answer", "").strip().lower() in ("nu stiu", "n/a", "skip")
            )
        ]
        answered_count = len(answered_rounds)
        total_planned = len(topics) if topics else len(qa_rounds)
        uncovered_topics = topics[covered_count:] if (topics and covered_count < len(topics)) else []

        # Collect unassessed planned competencies that were never reached
        unassessed_items = []
        if uncovered_topics:
            base_qid = len(qa_rounds)
            for u_idx, u_topic in enumerate(uncovered_topics, start=1):
                clean_top = u_topic.replace("\n", " ").strip()
                unassessed_items.append({
                    "question_id": base_qid + u_idx,
                    "question_text": clean_top,
                    "response_text": "[NO RESPONSE - SESSION CONCLUDED BEFORE REACHING TOPIC]",
                    "explanation": (
                        "Competență tehnică esențială rămasă neevaluată din cauza finalizării anticipate a sesiunii de interviu."
                        if is_ro
                        else "Core technical competency remained unassessed due to early conclusion of the interview session."
                    ),
                })

        overall_score = float(eval_report.get("overall_score", 0.0))
        summary_text = eval_report.get("summary", "Technical interview evaluation completed.")
        strengths = eval_report.get("strengths", [])
        weaknesses = eval_report.get("weaknesses", [])

        # Append unassessed topics to weaknesses
        if unassessed_items:
            if isinstance(weaknesses, list):
                weaknesses = list(weaknesses) + unassessed_items
            else:
                weaknesses = unassessed_items

        rec_label = eval_report.get("recommendation", "hire").replace("_", " ").title()

        # Deterministic Session Coverage Governance
        if total_planned > 0 and answered_count < total_planned:
            coverage_ratio = max(0.0, min(1.0, answered_count / total_planned))
            scaled_score = round(overall_score * coverage_ratio, 1)
            overall_score = max(1.0, scaled_score)

            if coverage_ratio < 0.50:
                rec_label = "No Hire"
            elif coverage_ratio < 0.70 and rec_label.lower() in ("strong hire", "hire"):
                rec_label = "Leaning No Hire"

            cov_pct = round(coverage_ratio * 100)
            cov_prefix = (
                f"**Acoperire Sesiune:** Candidatul a răspuns la {answered_count} din cele {total_planned} competențe planificate ({cov_pct}% acoperire). "
                if is_ro
                else f"**Session Coverage:** Candidate answered {answered_count} of {total_planned} planned core competencies ({cov_pct}% coverage). "
            )
            summary_text = f"{cov_prefix}{summary_text}"

        strengths_str = _format_eval_feedback_section(strengths, is_ro=is_ro, qa_rounds_map=qa_rounds_map)
        weaknesses_str = _format_eval_feedback_section(weaknesses, is_ro=is_ro, qa_rounds_map=qa_rounds_map)

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

    def _has_evaluation_report(self, interview: Interview) -> bool:
        """Check if an assistant evaluation report already exists in interview messages."""
        for m in reversed(interview.messages):
            if m.role == MessageRole.ASSISTANT:
                content_lower = (m.content or "").lower()
                if (
                    "overall ai assessment" in content_lower
                    or "evaluare general" in content_lower
                    or "recruiter evaluation report" in content_lower
                    or "arii de îmbunătățire" in content_lower
                    or "arii de imbunatatire" in content_lower
                    or "areas for improvement" in content_lower
                ):
                    return True
        return False

    async def complete_interview(self, db: AsyncSession, interview_id: str) -> Optional[Interview]:
        """Mark an interview as completed, generate AI evaluation report, and ensure strict state-machine idempotency."""
        interview = await self.get_interview(db, interview_id)
        if not interview:
            return None

        # 1. If already COMPLETED and already has evaluation report, return immediately
        if interview.status == InterviewStatus.COMPLETED and self._has_evaluation_report(interview):
            return interview

        # 2. Acquire lock to serialize evaluation generation for this interview ID
        if interview_id not in self._eval_locks:
            self._eval_locks[interview_id] = asyncio.Lock()

        async with self._eval_locks[interview_id]:
            # Expire session cache to ensure fresh read of messages committed by other workers/connections
            db.expire_all()
            # Re-fetch fresh interview
            interview = await self.get_interview(db, interview_id)
            if not interview:
                return None

            if self._has_evaluation_report(interview):
                if interview.status != InterviewStatus.COMPLETED:
                    interview.status = InterviewStatus.COMPLETED
                    await db.commit()
                return interview

            # Mark status as FINISHING in DB immediately
            now = datetime.now(timezone.utc)
            if interview.status != InterviewStatus.FINISHING and interview.status != InterviewStatus.COMPLETED:
                interview.status = InterviewStatus.FINISHING
                interview.updated_at = now
                await db.commit()

            # Generate evaluation report (fail fast if LLM or evaluation fails)
            closing_content = await self._generate_evaluation_closing(interview)

            # Check if there is an existing wrap-up or evaluation message to replace
            existing_closing_msg = None
            for m in reversed(interview.messages):
                if m.role == MessageRole.ASSISTANT:
                    content_lower = (m.content or "").lower()
                    if (
                        "overall ai assessment" in content_lower
                        or "evaluare general" in content_lower
                        or "recruiter evaluation report" in content_lower
                        or "arii de îmbunătățire" in content_lower
                        or "arii de imbunatatire" in content_lower
                        or "key strengths" in content_lower
                        or "s-a încheiat" in content_lower
                        or "s-a incheiat" in content_lower
                        or "has concluded" in content_lower
                        or "thank you" in content_lower
                        or "mulțumim" in content_lower
                        or "multumim" in content_lower
                        or "[interview_complete]" in content_lower
                    ):
                        existing_closing_msg = m
                        break

            finish_time = datetime.now(timezone.utc)
            if existing_closing_msg is not None:
                existing_closing_msg.content = closing_content
                existing_closing_msg.updated_at = finish_time
            else:
                closing_msg = Message(
                    id=str(uuid.uuid4())[:8],
                    interview_id=interview_id,
                    role=MessageRole.ASSISTANT,
                    content=closing_content,
                    question_number=None,
                    created_at=finish_time,
                )
                db.add(closing_msg)

            interview.status = InterviewStatus.COMPLETED
            interview.updated_at = finish_time
            await db.commit()
            return await self.get_interview(db, interview.id)


interview_service = InterviewService()
