import re
from typing import Dict, Any, List, Optional
from llm.agent.state import InterviewState
from llm.prompts import (
    build_clarification_response_prompt,
    build_both_response_prompt,
    build_refusal_response_prompt,
    build_next_question_prompt,
    build_first_question_prompt,
    build_intro_prompt,
)
from llm.constants import CLARIFICATION_STEER_THRESHOLD

def _clean_candidate_display_name(raw_name: str) -> str:
    """Sanitize and clean candidate name for prompt interpolation."""
    if not raw_name:
        return "Candidate"
    name = re.sub(r"(?i)\b(?:cv|resume|curriculum|vitae|file|document)\b", "", raw_name)
    name = re.sub(r"[_\-\.]+", " ", name).strip()
    return name.title() if name else "Candidate"

def start_interview_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Start Interview.
    Generates the opening turn prompt (Greeting + First Technical Question on Topic 1).
    """
    job_title = state.get("job_title", "Software Engineer")
    job_description = state.get("job_description", "")
    exp_level = state.get("experience_level", "mid")
    company_name = state.get("company_name")
    candidate_name = _clean_candidate_display_name(state.get("candidate_name", ""))
    topics = state.get("topics_plan") or [f"Core {job_title} Engineering"]
    first_topic = topics[0] if topics else "Core Fundamentals"
    lang = state.get("language", "en")

    turn_prompt = build_first_question_prompt(
        job_title=job_title,
        job_description=job_description,
        experience_level=exp_level,
        company_name=company_name,
        cv_raw_text="",
        candidate_name=candidate_name,
        first_topic=first_topic,
        language=lang,
    )

    return {
        "active_question_number": 1,
        "assigned_q_num": 1,
        "active_question_status": "WAITING_ANSWER",
        "current_topic_index": 0,
        "topic_follow_up_count": 0,
        "turn_prompt": turn_prompt,
        "is_complete": False,
    }

def process_candidate_response_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Process Candidate Response (Router).
    Analyzes candidate input to classify intent and route conditionally in LangGraph:
    - LANGUAGE_SWITCH:ro / LANGUAGE_SWITCH:en
    - GREETING
    - CLARIFICATION
    - CLARIFICATION_AND_ANSWER
    - REFUSAL (Don't know / skip)
    - WRAP_UP (Explicit quit / Time expired)
    - ANSWER (Standard technical answer)
    """
    text = (state.get("candidate_message") or "").strip()
    active_status = state.get("active_question_status") or "WAITING_ANSWER"
    time_expired = state.get("time_expired", False)

    if time_expired:
        return {"intent": "WRAP_UP"}

    # 1. Language switch request
    lang_switch_patterns = [
        (r"(?i)\b(?:vorbi(?:m|ți)?|continu[ăa]m?|hai\s+s[ăa]\s+vorbim|putem\s+(?:continua|vorbi)|treci\s+pe|schimb[ăa]\s+(?:pe|în)?|r[ăa]spunde(?:m)?\s+în|switch(?:\s+to)?)\s+(?:și\s+)?(?:în|in)?\s*(?:limba\s+)?rom[âa]n[ăa]\b", "ro"),
        (r"(?i)\b(?:în|in)\s+(?:limba\s+)?rom[âa]n[ăa]\b", "ro"),
        (r"(?i)\b(?:speak(?:\s+in)?|continue(?:\s+in)?|switch(?:\s+to)?|can\s+we\s+(?:speak|switch(?:\s+to)?)|talk(?:\s+in)?|in)\s+(?:the\s+)?(?:language\s+)?english\b", "en"),
        (r"(?i)\b(?:în|in)\s+(?:limba\s+)?(?:english|englez[ăa])\b", "en"),
    ]
    for pattern, target_lang in lang_switch_patterns:
        if re.search(pattern, text):
            return {"intent": f"LANGUAGE_SWITCH:{target_lang}"}

    # 2. Greeting or Readiness
    if active_status in ("WAITING_GREETING", "INIT"):
        greeting_patterns = [
            r"(?i)\b(salut|bun[ăa]|bun[ăa]\s+ziua|hello|hi|hey|da|yes|sunt\s+gata|ready|putem\s+[îi]ncepe|let'?s\s+(?:start|begin)|start)\b"
        ]
        if any(re.search(p, text) for p in greeting_patterns):
            return {"intent": "GREETING"}

    # 3. Explicit Wrap-up request
    wrapup_patterns = [
        r"(?i)\b(termin[ăa]m|am\s+terminat|încheiem|stop\s+interviu|gata\s+interviul|end\s+interview|finish\s+interview|i'?m\s+done)\b",
    ]
    if any(re.search(p, text) for p in wrapup_patterns) and len(text.split()) <= 10:
        return {"intent": "WRAP_UP"}

    # 4. Profane language
    if re.search(r"(?i)\b(?:pula|pizda|muie|futu|dracu|shit|fuck|bitch|asshole|idiot|prost|retardat)\b", text):
        return {"intent": "PROFANE_LANGUAGE"}

    # 5. Off-topic / Prompt Injection
    if re.search(r"(?i)\b(?:ignore\s+all\s+previous|cookie\s+recipe|reteta|vremea|weather|gluma|joke|tell\s+me\s+a\s+story|danseaza|canta)\b", text):
        return {"intent": "OFF_TOPIC"}

    # 6. Refusal / Don't Know / Skip
    refusal_patterns = [
        r"(?i)\b(nu\s+știu|nu\s+stiu|nu\s+am\s+lucrat|nu\s+am\s+folosit|nu\s+am\s+experienț[ăa]|nu\s+cunosc|nu\s+am\s+f[ăa]cut|skip|pass|s[ăa]\s+s[ăa]rim|trecem\s+mai\s+departe|alt[ăa]\s+[îi]ntrebare|urm[ăa]toarea\s+[îi]ntrebare|i\s+don'?t\s+know|haven'?t\s+worked|no\s+experience|skip\s+this|pass\s+this|nu\s+aș\s+ști)\b",
        r"(?i)^\s*(?:și\s+)?(?:continu[ăa]m\??|putem\s+continua\??|s[ăa]\s+continu[ăa]m\??|next|mai\s+departe|mergem\s+mai\s+departe)\s*$",
    ]
    if any(re.search(pat, text) for pat in refusal_patterns):
        words = text.split()
        if len(words) <= 12 or not re.search(r"(?i)\b(aș\s+folosi|aș\s+alege|aș\s+face|prefer\s+s[ăa]|soluția\s+mea|[îi]n\s+schimb|i\s+would|instead|my\s+approach)\b", text):
            return {"intent": "REFUSAL"}


    # 5. Clarification Inquiries
    confusion_patterns = [
        r"(?i)\b(nu\s+[îi]nțeleg|nu\s+prea\s+[îi]nțeleg|nu\s+am\s+[îi]nțeles|i\s+don'?t\s+understand)\b",
        r"(?i)\b(poți\s+(?:s[ăa]\s+)?(?:clarifici|clarific[ăa]|reformulezi|detaliezi|explici)|could\s+you\s+(?:clarify|rephrase|explain)|can\s+you\s+(?:clarify|rephrase|explain))\b",
        r"(?i)\b(clarific[ăa]|clarificare|rephrase|clarify|detaliaz[ăa])\b",
        r"(?i)\b(nu\s+(?:îmi\s+)?e(?:ste)?\s+(?:foarte\s+)?clar|it'?s\s+not\s+clear|not\s+very\s+clear|unclear)\b",
        r"(?i)\b(la\s+ce\s+te\s+referi|what\s+do\s+you\s+mean|what\s+does\s+that\s+mean|ce\s+vrei\s+s[ăa]\s+spui|ce\s+ai\s+vrea)\b",
        r"(?i)\b(ce\s+[îi]nseamn[ăa]|ce\s+e\s+aia|ce\s+este|ce\s+reprezint[ăa]|what\s+is|what\s+does\s+.*\s+mean|what\s+are)\b",
        r"(?i)\b(te\s+referi\s+la|do\s+you\s+mean|ce\s+parte|care\s+dintre|sau\s+ambele|despre\s+ce|ce\s+anume)\b",
        r"(?i)\b(pot\s+folosi|pot\s+s[ăa]\s+folosesc|can\s+i\s+use|should\s+i\s+use|is\s+it\s+allowed|avem\s+voie)\b",
    ]
    is_clarification = any(re.search(pat, text) for pat in confusion_patterns)
    is_question_message = "?" in text and not bool(re.search(r"(?i)\b(aș\s+folosi|aș\s+alege|aș\s+face|aș\s+implementa|soluția\s+mea|[îi]n\s+schimb|i\s+would|i\s+prefer)\b", text))

    if is_clarification or is_question_message:
        has_substantive_answer = (
            len(text.split()) >= 15
            and bool(re.search(r"(?i)\b(aș\s+folosi|aș\s+alege|aș\s+face|aș\s+implementa|aș\s+crea|pentru\s+c[ăa]|deoarece|[îi]n\s+schimb|i\s+would|because|i\s+prefer|my\s+solution|implementing|using)\b", text))
        )
        if has_substantive_answer:
            return {"intent": "CLARIFICATION_AND_ANSWER"}
        return {"intent": "CLARIFICATION"}

    return {"intent": "ANSWER"}

def detect_clarification_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Detect & Answer Clarification.
    Answers candidate's clarifying question and redirects back to active technical question.
    """
    consecutive = (state.get("consecutive_clarifications") or 0) + 1
    display_name = _clean_candidate_display_name(state.get("candidate_name", ""))
    active_q = state.get("active_question_text") or "Active technical question"

    turn_prompt = build_clarification_response_prompt(
        job_title=state.get("job_title", "Software Engineer"),
        experience_level=state.get("experience_level", "mid"),
        candidate_name=display_name,
        active_question_text=active_q,
        candidate_query=state.get("candidate_message", ""),
        consecutive_clarifications=consecutive,
        clarification_threshold=CLARIFICATION_STEER_THRESHOLD,
        language=state.get("language", "ro"),
    )

    return {
        "consecutive_clarifications": consecutive,
        "turn_prompt": turn_prompt,
        "assigned_q_num": state.get("active_question_number", 1),
        "is_complete": False,
    }

def detect_refusal_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Detect Refusal / Skip.
    Acknowledges lack of experience supportively, resets clarification counter,
    and advances topic index.
    """
    cur_idx = state.get("current_topic_index", 0)
    topics = state.get("topics_plan") or [f"Core {state.get('job_title', 'Engineering')}"]
    next_idx = cur_idx + 1
    next_topic = topics[min(next_idx, len(topics) - 1)] if topics else "System Architecture"
    display_name = _clean_candidate_display_name(state.get("candidate_name", ""))
    is_complete = bool(next_idx >= len(topics) or state.get("time_expired", False))

    turn_prompt = build_refusal_response_prompt(
        job_title=state.get("job_title", "Software Engineer"),
        experience_level=state.get("experience_level", "mid"),
        candidate_name=display_name,
        active_question_text=state.get("active_question_text") or "Active question",
        candidate_message=state.get("candidate_message", ""),
        next_topic=next_topic,
        previous_questions=state.get("previous_questions", []),
        language=state.get("language", "ro"),
    )

    next_q_num = (state.get("active_question_number") or 1) + 1
    return {
        "consecutive_clarifications": 0,
        "current_topic_index": next_idx,
        "topic_follow_up_count": 0,
        "active_question_number": next_q_num,
        "assigned_q_num": next_q_num,
        "turn_prompt": turn_prompt,
        "is_complete": is_complete,
    }

def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Evaluate Answer.
    Assesses candidate answer, checks if a technical follow-up is needed,
    updates assessed topics, and checks termination conditions (time or topics exhausted).
    """
    cur_idx = state.get("current_topic_index", 0)
    topics = state.get("topics_plan") or [f"Core {state.get('job_title', 'Engineering')}"]
    cur_topic = topics[min(cur_idx, len(topics) - 1)] if topics else "Core Fundamentals"

    assessed = list(state.get("assessed_topics") or [])
    if cur_topic not in assessed:
        assessed.append(cur_topic)

    text = (state.get("candidate_message") or "").strip()
    words = text.split()
    follow_up_count = state.get("topic_follow_up_count", 0)
    time_expired = state.get("time_expired", False)

    # Check if a follow-up probe is appropriate:
    # Trigger follow-up if answer is brief / shallow (< 8 words) and not yet probed on this topic
    needs_follow_up = (
        1 <= len(words) < 8
        and follow_up_count == 0
        and not time_expired
        and (cur_idx < len(topics) - 1)
    )

    if needs_follow_up:
        return {
            "consecutive_clarifications": 0,
            "assessed_topics": assessed,
            "needs_follow_up": True,
            "is_complete": False,
        }

    # Otherwise, standard topic advancement
    next_idx = cur_idx + 1
    all_topics_assessed = (next_idx >= len(topics))
    is_complete = bool(time_expired or all_topics_assessed)

    return {
        "consecutive_clarifications": 0,
        "assessed_topics": assessed,
        "current_topic_index": next_idx,
        "topic_follow_up_count": 0,
        "needs_follow_up": False,
        "is_complete": is_complete,
    }

def generate_follow_up_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Generate Follow-up.
    Generates a targeted deep-dive technical question probing candidate's previous partial answer.
    """
    cur_idx = state.get("current_topic_index", 0)
    topics = state.get("topics_plan") or [f"Core {state.get('job_title', 'Engineering')}"]
    cur_topic = topics[min(cur_idx, len(topics) - 1)] if topics else "Active Competency"
    display_name = _clean_candidate_display_name(state.get("candidate_name", ""))

    turn_prompt = build_next_question_prompt(
        job_title=state.get("job_title", "Software Engineer"),
        experience_level=state.get("experience_level", "mid"),
        candidate_name=display_name,
        last_question=state.get("active_question_text") or "Active question",
        candidate_answer=state.get("candidate_message", ""),
        next_topic=cur_topic,
        is_follow_up=True,
        previous_questions=state.get("previous_questions", []),
        language=state.get("language", "ro"),
    )

    next_q_num = (state.get("active_question_number") or 1) + 1
    return {
        "topic_follow_up_count": (state.get("topic_follow_up_count", 0) + 1),
        "active_question_number": next_q_num,
        "assigned_q_num": next_q_num,
        "turn_prompt": turn_prompt,
        "active_question_status": "WAITING_ANSWER",
    }

def move_to_next_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Move to Next Question.
    Transitions to the next competency in topics_plan and formulates the active technical question.
    """
    cur_idx = state.get("current_topic_index", 0)
    topics = state.get("topics_plan") or [f"Core {state.get('job_title', 'Engineering')}"]
    next_topic = topics[min(cur_idx, len(topics) - 1)] if topics else "System Architecture"
    display_name = _clean_candidate_display_name(state.get("candidate_name", ""))

    intent = state.get("intent", "ANSWER")
    if intent == "CLARIFICATION_AND_ANSWER":
        turn_prompt = build_both_response_prompt(
            job_title=state.get("job_title", "Software Engineer"),
            experience_level=state.get("experience_level", "mid"),
            candidate_name=display_name,
            active_question_text=state.get("active_question_text") or "Active question",
            candidate_content=state.get("candidate_message", ""),
            next_topic=next_topic,
            previous_questions=state.get("previous_questions", []),
            language=state.get("language", "ro"),
        )
    else:
        turn_prompt = build_next_question_prompt(
            job_title=state.get("job_title", "Software Engineer"),
            experience_level=state.get("experience_level", "mid"),
            candidate_name=display_name,
            last_question=state.get("active_question_text") or "Active question",
            candidate_answer=state.get("candidate_message", ""),
            next_topic=next_topic,
            is_follow_up=False,
            previous_questions=state.get("previous_questions", []),
            language=state.get("language", "ro"),
        )

    next_q_num = (state.get("active_question_number") or 1) + 1
    return {
        "active_question_number": next_q_num,
        "assigned_q_num": next_q_num,
        "turn_prompt": turn_prompt,
        "active_question_status": "WAITING_ANSWER",
    }

def language_switch_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Language Switch.
    Acknowledges language change request and re-poses the active technical question in target language.
    """
    intent = state.get("intent", "LANGUAGE_SWITCH:ro")
    new_lang = intent.split(":")[1] if ":" in intent else "ro"
    candidate_content = state.get("candidate_message", "")
    active_q = state.get("active_question_text") or "the current technical question"

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

    return {
        "language": new_lang,
        "turn_prompt": turn_prompt,
        "assigned_q_num": state.get("active_question_number", 1),
        "is_complete": False,
    }

def generate_final_evaluation_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Generate Final Evaluation / Wrap-up.
    Generates closing message, appends [INTERVIEW_COMPLETE], and transitions to completed status.
    """
    display_name = _clean_candidate_display_name(state.get("candidate_name", ""))
    turn_prompt = build_next_question_prompt(
        job_title=state.get("job_title", "Software Engineer"),
        experience_level=state.get("experience_level", "mid"),
        candidate_name=display_name,
        last_question=state.get("active_question_text") or "Active question",
        candidate_answer=state.get("candidate_message", ""),
        next_topic="Conclusion",
        is_final_wrap_up=True,
        previous_questions=state.get("previous_questions", []),
        language=state.get("language", "ro"),
    )

    return {
        "is_complete": True,
        "turn_prompt": turn_prompt,
        "active_question_status": "COMPLETED",
    }

def guardrail_node(state: InterviewState) -> Dict[str, Any]:
    """
    Workflow Step: Guardrail Response.
    Politely redirects inappropriate language or off-topic queries back to active question.
    """
    intent = state.get("intent", "OFF_TOPIC")
    active_q = state.get("active_question_text") or "the current technical question"
    candidate_content = state.get("candidate_message", "")
    lang = state.get("language", "ro")

    if intent == "PROFANE_LANGUAGE":
        if lang == "ro":
            turn_prompt = (
                f"Candidatul a folosit un limbaj nepotrivit ('{candidate_content[:60]}').\n"
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
    else:
        if lang == "ro":
            turn_prompt = f"Candidatul a trimis un mesaj în afara subiectului sau o glumă ('{candidate_content[:60]}'). Refuză politicos în 1 propoziție scurtă și revino ferm la întrebarea activă: \"{active_q}\"."
        else:
            turn_prompt = f"The candidate sent an off-topic query or joke ('{candidate_content[:60]}'). Politely decline in 1 brief sentence and firmly return to the active question: \"{active_q}\"."

    return {
        "turn_prompt": turn_prompt,
        "assigned_q_num": state.get("active_question_number", 1),
        "is_complete": False,
    }

