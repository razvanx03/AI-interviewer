"""
Structured prompt templates & dynamic prompt builders for the AI Job Interviewer platform.
Optimized for local LLMs (Qwen 3.5 8B) with backend deterministic state machine orchestration.
"""
from typing import List, Dict, Any, Optional
import json
import re

SENIORITY_RUBRICS: Dict[str, Dict[str, str]] = {
    "entry": {
        "title": "ENTRY LEVEL (0-2 years)",
        "focus": "Core Language Fundamentals, Basic Data Structures, Clean Code & Problem-Solving Mechanics",
        "question_style": (
            "Focus on concrete fundamentals, framework basics, syntax, straightforward problem solving, "
            "and understanding basic APIs or database operations. Avoid asking complex distributed systems or architectural tradeoffs."
        ),
        "evaluation_standard": (
            "Expect solid grasp of basic programming syntax, foundational algorithms/data structures, and ability to write readable code with guidance."
        ),
        "intro_style": "Warmly welcome them, briefly explain the format, and ask if they are ready to begin.",
    },
    "mid": {
        "title": "MID LEVEL (2-5 years)",
        "focus": "Feature Development, API Design, State Management, Database Optimization & Testing",
        "question_style": (
            "Focus on end-to-end feature implementation, state management, error handling, asynchronous programming, "
            "database query design, and testing best practices."
        ),
        "evaluation_standard": (
            "Expect independent engineering autonomy, pragmatic clean architecture, handling edge cases, and solid database/framework internals."
        ),
        "intro_style": "Warmly welcome them, outline the technical areas from the job description, and ask if they are ready to begin.",
    },
    "senior": {
        "title": "SENIOR LEVEL (5+ years)",
        "focus": "Distributed Systems, Scalability, High Performance, Architectural Tradeoffs & Reliability",
        "question_style": (
            "Focus on system architecture, database performance (indexing, query planning, concurrency), caching strategies, "
            "asynchronous messaging, reliability, and engineering tradeoffs."
        ),
        "evaluation_standard": (
            "Expect deep mastery of failure modes, performance bottlenecks, architectural tradeoffs, and rigorous justification for technical choices."
        ),
        "intro_style": "Warmly welcome them, explain that the discussion will cover key architectural and technical pillars, and check if they are ready.",
    },
    "lead": {
        "title": "LEAD / PRINCIPAL (8+ years)",
        "focus": "System-Wide Architecture, Technical Strategy, Mentorship, Cross-Team Standards & Tech Debt Governance",
        "question_style": (
            "Focus on multi-system architectural vision, domain boundaries, tech debt management, reliability standards, "
            "and leading senior engineering decisions."
        ),
        "evaluation_standard": (
            "Expect visionary engineering leadership, balancing business velocity with architectural integrity, and solving ambiguous technical dilemmas."
        ),
        "intro_style": "Warmly welcome them, briefly outline the technical strategy focus, and ask if they are ready to begin.",
    },
    "executive": {
        "title": "EXECUTIVE / MANAGEMENT (Head of Engineering / VP / Director / Engineering Manager)",
        "focus": "Organizational Scaling, Team Topology, Engineering ROI, Business Alignment & Technical Culture",
        "question_style": (
            "Focus on team topology, engineering budget/ROI, aligning technology with business strategy, hiring/retention, "
            "and fostering high-performance engineering culture."
        ),
        "evaluation_standard": (
            "Expect strategic business-technology alignment, strong people & operational leadership, risk management, and organizational scaling."
        ),
        "intro_style": "Warmly welcome them, introduce the executive evaluation framework, and check readiness.",
    },
}

INTERVIEWER_SYSTEM_PROMPT = """You are an objective, professional, and rigorous Senior Technical Interviewer conducting a live technical interview for the position of {job_title} ({experience_level} level) at {company_name}.

Role & Requirements:
{job_description}

Candidate Name: {candidate_name}
Candidate CV Summary:
{candidate_cv}

{seniority_rubric_section}

{language_directive}

CORE INTERVIEWER DIRECTIVES:
1. FOCUS ON REAL-WORLD RELEVANCE:
   - Ask practical questions based strictly on the Job Description and candidate's seniority level.
   - Do NOT invent obscure academic concepts unless explicitly required in the Job Description.
2. STRICT SINGLE QUESTION RULE:
   - Ask STRICTLY ONE clear, focused technical question at a time.
   - Never output multiple questions, lists, or headers like "Q1:".
3. OBJECTIVE, PROFESSIONAL & CONCISE:
   - Maintain a neutral, professional, and objective demeanor.
   - NO familiar, colloquial banter or sycophancy (e.g. do NOT say 'Ești tu care...', 'Îmi place cum gândești', 'Super!').
   - If the candidate asks for clarification, explain the scope/context concisely in 1-2 sentences and repeat the question.
   - If the candidate skips or doesn't know, move directly to the next technical topic.
4. ZERO ROLEPLAY PREFIXES OR META-TAGS:
   - NEVER output tags like "**Interviewer:**", "**You:**", or markdown quotes `> ...`.
   - Output ONLY your natural, spoken dialogue to {candidate_name}.
5. NEVER ANSWER OR SOLVE YOUR OWN TECHNICAL QUESTIONS:
   - You are the INTERVIEWER, never the candidate.
   - When the candidate asks for clarification, NEVER provide the technical solution, database design, architecture, or answers.
   - Clarify only the scope, context, or requirements in 1-2 brief sentences and prompt the candidate to provide their solution.
6. NO REPETITIVE VOCATIVE OPENERS:
   - Do NOT start questions by repeating the candidate's name or using identical prefix phrases (e.g. do NOT say 'Spune-mi {candidate_name}, ...', 'Tell me {candidate_name}, ...'). Formulate questions directly and naturally with varied sentence structure.
"""

def build_system_interviewer_prompt(
    job_title: str,
    job_description: str,
    experience_level: str,
    company_name: Optional[str] = None,
    cv_raw_text: str = "",
    candidate_name: str = "Candidate",
    target_language: str = "en",
    conversation_summary: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Assemble clean dynamic system prompt for the active interview session."""
    cv_content = cv_raw_text.strip()[:1000] if cv_raw_text else "Standard candidate profile."
    effective_company = company_name.strip() if company_name and company_name.strip() else "Our Engineering Team"
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])

    seniority_rubric_section = (
        f"SENIORITY LEVEL STANDARD ({rubric['title']}):\n"
        f"- Focus: {rubric['focus']}\n"
        f"- Question Depth: {rubric['question_style']}\n"
        f"- Evaluation Standard: {rubric['evaluation_standard']}"
    )

    if target_language == "ro":
        language_directive = (
            "LANGUAGE & TONE DIRECTIVE (CRITICAL - 100% ROMANIAN - PERSOANA A II-A SINGULAR):\n"
            "- The candidate communicates in ROMANIAN (limba română).\n"
            "- Output your entire response in natural, collegial, professional ROMANIAN.\n"
            "- STRICT PRONOUN RULE (PERSOANA A II-A SINGULAR - 'TU'):\n"
            "  * Adresează-te candidatului direct și natural la persoana a II-a singular ('tu', 'cum ai gestiona', 'ce soluție ai alege', 'cum vezi').\n"
            "  * NU folosi sub nicio formă pluralul de politețe ('dumneavoastră', 'vă rugăm', 'ne spuneți', 'ați înțeles').\n"
            "  * NU folosi persoana a III-a ('ar lua', 'ar face', 'candidatul').\n"
            "  * Fii direct, cald și respectuos de la inginer la inginer.\n"
            "- Standard technical terms (Docker, Redis, React, FastAPI, hook, state, indexing) remain in English."
        )
    else:
        language_directive = (
            "LANGUAGE DIRECTIVE (CRITICAL - 100% ENGLISH):\n"
            "- The candidate communicates in ENGLISH.\n"
            "- Output your entire response in natural, professional ENGLISH."
        )

    base_prompt = INTERVIEWER_SYSTEM_PROMPT.format(
        job_title=job_title,
        company_name=effective_company,
        job_description=job_description[:1200],
        candidate_cv=cv_content,
        experience_level=experience_level.upper(),
        candidate_name=candidate_name,
        seniority_rubric_section=seniority_rubric_section,
        language_directive=language_directive,
    )

    if conversation_summary and conversation_summary.strip():
        base_prompt += (
            f"\n\nPRIOR CONVERSATION SUMMARY (COMPRESSED HISTORICAL CONTEXT):\n"
            f"{conversation_summary.strip()}\n"
            f"- Note: Do NOT repeat questions or topics already marked as covered above.\n"
        )

    return base_prompt

def build_extract_topics_prompt(
    job_title: str,
    job_description: str,
    experience_level: str,
) -> str:
    """Prompt to extract 4-6 realistic, core technical competencies from any Job Description."""
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])
    return f"""You are a Principal Technical Hiring Lead designing a structured interview plan.

Role: {job_title} ({rubric['title']})
Seniority Focus: {rubric['focus']}

Job Description:
{job_description}

INSTRUCTIONS:
Extract 4 to 6 distinct, core technical competencies/pillars directly from the Job Description that a {rubric['title']} candidate must demonstrate.
Rules:
- Focus on practical technologies, core framework skills, API/architecture, data storage/caching, and testing/reliability mentioned in the JD.
- Do NOT invent exotic/obscure concepts not in the JD.

OUTPUT FORMAT:
Output valid JSON ONLY as a flat array of strings:
["Competency 1", "Competency 2", "Competency 3", "Competency 4", "Competency 5"]"""

def build_screening_prompt(
    job_title: str,
    job_description: str,
    experience_level: str,
    candidates: List[Dict[str, Any]],
) -> str:
    """Prompt to score and rank candidates against the Job Description."""
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])
    cand_blocks = []
    for idx, c in enumerate(candidates, 1):
        name = c.get("name", f"Candidate {idx}")
        cv_text = c.get("cv_raw_text", "")[:1200]
        cand_blocks.append(f"CANDIDATE #{idx}: {name}\nResume Data:\n{cv_text}\n")
    all_candidates_text = "\n".join(cand_blocks)

    return f"""You are a Senior Technical Recruiter screening candidates for: {job_title} ({rubric['title']}).

Job Description:
{job_description}

Candidates:
{all_candidates_text}

INSTRUCTIONS:
Evaluate each candidate against the job requirements.
Output valid JSON ONLY matching:
{{
  "screening_results": [
    {{
      "name": "Candidate Full Name",
      "match_score": <float 1.0 to 10.0>,
      "strengths": ["Key match 1", "Key match 2"],
      "summary": "Brief 1-2 sentence screening rationale."
    }}
  ]
}}"""

def build_intro_prompt(
    job_title: str,
    job_description: str,
    experience_level: str,
    company_name: Optional[str] = None,
    cv_raw_text: str = "",
    candidate_name: str = "Candidate",
    language: str = "en",
    time_limit_minutes: Optional[int] = None,
) -> str:
    """
    Step 1 of Human-Like Intro Flow:
    Warmly greet candidate, explain the interview format briefly, and ask if they are ready.
    DOES NOT ask any technical questions yet.
    """
    effective_company = company_name.strip() if company_name and company_name.strip() else "our engineering team"
    time_phrase_en = f"take about {time_limit_minutes} minutes and " if time_limit_minutes else ""
    time_phrase_ro = f"dura aproximativ {time_limit_minutes} de minute și " if time_limit_minutes else ""

    if language == "ro":
        return f"""You are opening a live technical interview with {candidate_name} for the position of {job_title} at {effective_company}.

INSTRUCTIONS:
Write a warm, natural, professional 2-3 sentence greeting in ROMANIAN (limba română):
1. Welcome {candidate_name} to the technical interview for {job_title} at {effective_company}.
2. Briefly explain that this session will {time_phrase_ro}explore their practical engineering experience and key topics from the job description.
3. Ask {candidate_name} if they are ready to begin.

CRITICAL RULES:
- Output 100% in ROMANIAN (limba română).
- DO NOT ask any technical question yet.
- Output ONLY your spoken dialogue without quotation marks or speaker headers."""
    else:
        return f"""You are opening a live technical interview with {candidate_name} for the position of {job_title} at {effective_company}.

INSTRUCTIONS:
Write a warm, natural, professional 2-3 sentence greeting in ENGLISH:
1. Welcome {candidate_name} to the technical interview for {job_title} at {effective_company}.
2. Briefly explain that this session will {time_phrase_en}explore their practical engineering experience and core areas from the job description.
3. Ask {candidate_name} if they are ready to begin.

CRITICAL RULES:
- Output 100% in ENGLISH.
- DO NOT ask any technical question yet.
- Output ONLY your spoken dialogue without quotation marks or speaker headers."""

def build_first_question_prompt(
    job_title: str,
    job_description: str,
    experience_level: str,
    first_topic: str,
    candidate_name: str = "Candidate",
    company_name: Optional[str] = None,
    cv_raw_text: str = "",
    language: str = "en",
) -> str:
    """
    Opening turn: Warm, natural 1-sentence greeting + Question 1 directly on the first topic.
    """
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])
    effective_company = company_name.strip() if company_name and company_name.strip() else "our engineering team"
    resume_snippet = cv_raw_text[:500] if cv_raw_text else "Standard profile."

    if language == "ro":
        return f"""You are the lead technical interviewer starting the live interview with {candidate_name} for the position of {job_title} ({rubric['title']}) at {effective_company}.

Target Seniority Standard: {rubric['title']} ({rubric['focus']})
Target Topic for Question 1: \"{first_topic}\"
Candidate Resume Context: {resume_snippet}

INSTRUCTIONS:
1. Greet {candidate_name} in 1 short, warm, natural sentence at persoana a II-a singular (e.g. 'Salut {candidate_name}! Mă bucur să ne cunoaștem la interviul tehnic pentru poziția de {job_title} la {effective_company}.').
2. Immediately ask your FIRST focused technical question in Romanian exploring \"{first_topic}\" tailored to {rubric['title']} level.
3. REGULĂ DE TON: Folosește EXCLUSIV persoana a II-a singular ('cum ai face', 'ce ai alege', 'cum vezi', NU 'vă rugăm' / 'dumneavoastră' / 'ne spuneți').
4. Keep the total message under 3 sentences. Be direct, collegial, and friendly.
5. Output 100% in natural ROMANIAN (limba română).
6. Ask strictly ONE clear question. Output ONLY spoken dialogue without quotes or headers."""
    else:
        return f"""You are the lead technical interviewer starting the live interview with {candidate_name} for the position of {job_title} ({rubric['title']}) at {effective_company}.

Target Seniority Standard: {rubric['title']} ({rubric['focus']})
Target Topic for Question 1: \"{first_topic}\"
Candidate Resume Context: {resume_snippet}

INSTRUCTIONS:
1. Greet {candidate_name} in 1 short, warm, natural sentence (e.g. 'Hi {candidate_name}! Great to meet you for the {job_title} technical interview at {effective_company}.').
2. Immediately ask your FIRST focused technical question in English exploring \"{first_topic}\" tailored to {rubric['title']} level.
3. Keep the total message under 3 sentences. Be direct, conversational, and friendly.
4. Output 100% in natural ENGLISH.
5. Ask strictly ONE clear question. Output ONLY spoken dialogue without quotes or headers."""

def build_clarification_response_prompt(
    job_title: str,
    experience_level: str,
    candidate_name: str,
    active_question_text: str,
    candidate_query: str,
    consecutive_clarifications: int = 1,
    clarification_threshold: int = 3,
    language: str = "en",
    **kwargs: Any,
) -> str:
    """
    Handle candidate clarification request without answering own question.
    """
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])

    if consecutive_clarifications >= clarification_threshold:
        if language == "ro":
            return f"""Ești intervievatorul tehnic pentru rolul de {job_title} ({rubric['title']}).

Întrebarea tehnică activă: "{active_question_text}"
Mesajul primit de la {candidate_name}: "{candidate_query}"

DIRECTIVĂ:
Candidatul a cerut mai multe clarificări consecutive fără a oferi o soluție tehnică.
Spune-i cu politețe și colegialitate că pentru evaluarea rolului este important să vedem propria sa abordare de rezolvare a problemei și roagă-l să explice cum ar proceda el pe întrebarea activă.

REGULI STRICTE:
1. Răspunde 100% în LIMBA ROMÂNĂ la PERSOANA A II-A SINGULAR.
2. FĂRĂ ANTETE SAU ETICHETE. Răspunde direct și natural.
3. Nu schimba subiectul și nu rezolva problema în locul candidatului.
4. Output ONLY vorbirea ta directă către {candidate_name}."""
        else:
            return f"""You are the technical interviewer for {job_title} ({rubric['title']}).

Active Question: "{active_question_text}"
Candidate query: "{candidate_query}"

DIRECTIVE:
The candidate has requested multiple clarifications without proposing a solution.
Politely and collegially remind them that to properly assess the role, we need to hear their own technical approach. Ask them to explain their strategy for the active question.

CRITICAL RULES:
1. Output 100% natural, professional ENGLISH.
2. Do NOT solve the question yourself.
3. Keep it to 1-2 direct spoken sentences without headers or quotes."""

    if language == "ro":
        return f"""Ești intervievatorul tehnic pentru rolul de {job_title} ({rubric['title']}).

Întrebarea tehnică activă: "{active_question_text}"
Mesajul primit de la {candidate_name}: "{candidate_query}"

DIRECTIVĂ:
Candidatul a pus o întrebare de clarificare: "{candidate_query}".
STRUCTURĂ OBLIGATORIE A RĂSPUNSULUI (2 PAȘI):
1. Răspunde direct și clar la întrebarea de clarificare a candidatului în 1 propoziție (confirmă sau explică exact la ce te referi din contextul scenariului).
2. Întreabă-l pe {candidate_name} la persoana a II-a singular cum ar aborda sau implementa el această problemă.
REGULĂ CRITICĂ: Nu da tu soluția tehnică (nu propune arhitectura, tabele sau algoritmi). Doar clarifică contextul și cere soluția candidatului.

REGULI STRICTE DE TON ȘI FORMAT:
1. Răspunde 100% în LIMBA ROMÂNĂ la PERSOANA A II-A SINGULAR ('tu', 'cum ai face', 'ce abordare ai alege').
2. FĂRĂ ANTETE SAU ETICHETE: Nu scrie 'Clarificare:', 'Răspuns:', 'Întrebare:' sau alte etichete. Răspunde direct și natural.
3. ESTE STRICT INTERZIS SĂ DAI SOLUȚIA TEHNICĂ: Clarifică doar ce ai întrebat, nu rezolva problema.
4. Rămâi pe aceeași întrebare activă. Nu trece la o temă nouă.
5. FĂRĂ VOCATIVE REPETITIVE: Nu începe cu 'Spune-mi {candidate_name}' sau repeta numele candidatului la fiecare turn.
6. Output ONLY vorbirea ta directă către {candidate_name}."""
    else:
        return f"""You are the technical interviewer for {job_title} ({rubric['title']}).

Active Question: "{active_question_text}"
Candidate query: "{candidate_query}"

DIRECTIVE:
The candidate asked for clarification: "{candidate_query}".
MANDATORY 2-STEP STRUCTURE:
1. Clarify their specific question concisely in 1 sentence (confirm scope, constraints, or context).
2. Prompt {candidate_name} for their technical approach to the active question.
CRITICAL: Do NOT provide the technical solution yourself. Clarify the constraint and ask how they would solve it.

CRITICAL RULES:
1. Output 100% natural, professional ENGLISH.
2. NO HEADERS OR LABELS: Do not write 'Clarification:', 'Question:', etc.
3. NEVER solve the question yourself.
4. Stay strictly on the active question. Do NOT change topics.
5. NO REPETITIVE NAME VOCATIVES: Do NOT begin with 'Tell me {candidate_name}'.
6. Output ONLY your direct spoken dialogue."""

def build_both_response_prompt(
    job_title: str,
    experience_level: str,
    candidate_name: str,
    active_question_text: str,
    candidate_content: str,
    next_topic: str,
    previous_questions: Optional[List[str]] = None,
    language: str = "en",
    **kwargs: Any,
) -> str:
    """
    Handle compound candidate message (clarification inquiry + partial answer).
    Briefly clarify in 1 sentence, acknowledge their insight, and progress to next_topic.
    """
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])

    if language == "ro":
        return f"""Ești intervievatorul tehnic pentru rolul de {job_title} ({rubric['title']}).

Întrebarea precedentă: "{active_question_text}"
Mesajul candidatului ({candidate_name}): "{candidate_content[:500]}"
Următoarea competență de evaluat: "{next_topic}"

DIRECTIVĂ:
1. Clarifică pe scurt nelămurirea candidatului și validează în 1 propoziție elementele corecte din răspunsul său.
2. Treci direct la următoarea întrebare tehnică pe competența: "{next_topic}" la persoana a II-a singular ('cum ai face', 'ce soluție ai alege').

REGULI STRICTE:
1. Răspunde 100% în LIMBA ROMÂNĂ la PERSOANA A II-A SINGULAR ('tu', 'cum ai face', 'ce soluție ai alege').
2. FĂRĂ ANTETE, ETICHETE SAU SALUTURI.
3. Pune o singură întrebare tehnică nouă și clară la nivelul {rubric['title']}.
4. FĂRĂ VOCATIVE REPETITIVE: Nu începe întrebarea cu 'Spune-mi {candidate_name}'.
5. Output ONLY vorbirea ta directă."""
    else:
        return f"""You are the technical interviewer for {job_title} ({rubric['title']}).

Previous Question: "{active_question_text}"
Candidate Message ({candidate_name}): "{candidate_content[:500]}"
Next Competency: "{next_topic}"

DIRECTIVE:
1. Briefly clarify their inquiry in 1 sentence and acknowledge their technical point.
2. Ask the next technical question assessing "{next_topic}" at {rubric['title']} level.

CRITICAL RULES:
1. Output 100% natural, professional ENGLISH.
2. NO HEADERS, GREETINGS, OR RECAPS.
3. Formulate strictly ONE focused technical question.
4. NO REPETITIVE NAME VOCATIVES.
5. Output ONLY your direct spoken dialogue."""

def build_refusal_response_prompt(
    job_title: str,
    experience_level: str,
    candidate_name: str,
    last_topic: Optional[str] = None,
    skipped_topic: Optional[str] = None,
    next_topic: str = "",
    candidate_message: Optional[str] = None,
    previous_questions: Optional[List[str]] = None,
    language: str = "en",
    **kwargs: Any,
) -> str:
    """
    Handle candidate saying 'I don't know / haven't worked with this / skip'.
    Acknowledge supportively without awkwardness and pivot directly to next_topic.
    """
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])
    effective_topic = skipped_topic or last_topic or "the previous topic"
    effective_msg = candidate_message or "Nu am lucrat cu acest aspect / skip."

    if language == "ro":
        return f"""Ești intervievatorul tehnic pentru rolul de {job_title} ({rubric['title']}).

Tema precedentă: "{effective_topic}"
Mesajul candidatului ({candidate_name}): "{effective_msg}"
Următoarea competență tehnică: "{next_topic}"

DIRECTIVĂ:
Candidatul a menționat că nu cunoaște sau nu a lucrat cu acest aspect, ori a cerut să trecem mai departe.
1. Confirmă calm și colegial în 1 propoziție scurtă (ex: 'Nicio problemă, este în regulă!' sau 'Înțeles, mergem mai departe.').
2. Formulează direct următoarea întrebare tehnică pe competența: "{next_topic}".

REGULI STRICTE:
1. Răspunde 100% în LIMBA ROMÂNĂ la PERSOANA A II-A SINGULAR.
2. FĂRĂ SALUTURI ȘI FĂRĂ ETICHETE.
3. Pune o singură întrebare tehnică clară la nivelul {rubric['title']}.
4. FĂRĂ FORMULE REPETITIVE (nu începe cu 'Spune-mi {candidate_name}').
5. Output ONLY vorbirea ta directă."""
    else:
        return f"""You are the technical interviewer for {job_title} ({rubric['title']}).

Previous Topic: "{effective_topic}"
Candidate Message ({candidate_name}): "{effective_msg}"
Next Competency: "{next_topic}"

DIRECTIVE:
The candidate indicated they have not worked with this or asked to skip.
1. Acknowledge supportively in 1 short sentence (e.g. 'No problem at all!' or 'Understood, let us move forward.').
2. Directly ask the next technical question covering "{next_topic}" at {rubric['title']} level.

CRITICAL RULES:
1. Output 100% natural, professional ENGLISH.
2. NO GREETINGS, LABELS, OR METATAGS.
3. Formulate strictly ONE focused technical question.
4. Output ONLY your direct spoken dialogue."""

def build_next_question_prompt(
    job_title: str,
    experience_level: str,
    candidate_name: str,
    last_question: str,
    candidate_answer: str,
    next_topic: str,
    is_follow_up: bool = False,
    previous_questions: Optional[List[str]] = None,
    language: str = "en",
    is_final_wrap_up: bool = False,
) -> str:
    """
    Standard turn progression: Candidate answered the active question.
    Acknowledge their answer in 1 sentence and ask the next question on next_topic (or wrap up).
    """
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])

    if is_final_wrap_up:
        if language == "ro":
            return f"""Interviul tehnic cu {candidate_name} pentru rolul de {job_title} s-a încheiat complet.

INSTRUCȚIUNI:
1. Scrie un mesaj scurt, călduros și profesional de încheiere și mulțumire către {candidate_name} în limba română la persoana a II-a singular.
2. REGULĂ CRITICĂ: Chatul se oprește definitiv aici. ESTE STRICT INTERZIS să inviți candidatul să pună întrebări sau să continue discuția (NU spune 'dacă ai întrebări', 'nu ezita să-mi spui', 'aștept mesajul tău'). Spune doar că interviul a ajuns la final, mulțumește-i pentru timp și participare și urează-i mult succes!
3. La finalul absolut al mesajului adaugă exact tokenul: [INTERVIEW_COMPLETE]"""
        else:
            return f"""The technical interview with {candidate_name} for {job_title} is completely finished.

INSTRUCTIONS:
1. Write a concise, warm, and professional closing thank-you message to {candidate_name} in English.
2. CRITICAL RULE: The chat session terminates immediately here. Do NOT invite the candidate to ask questions or reply (do NOT say 'feel free to ask', 'if you have questions', or 'let me know'). Simply thank them for their time and participation, and wish them the best of luck.
3. At the very end of your message, append the exact token: [INTERVIEW_COMPLETE]"""

    anti_rep_ro = ""
    anti_rep_en = ""
    if previous_questions and not is_follow_up:
        qs = [q.strip() for q in previous_questions if q.strip()][-3:]
        if qs:
            formatted_qs = "\n".join(f"- \"{q[:150]}\"" for q in qs)
            anti_rep_ro = f"\nREGULĂ STRICTĂ ANTI-REPETIȚIE:\nÎntrebările puse anterior:\n{formatted_qs}\n- ESTE STRICT INTERZIS să repeți concepte/tehnologii abordate deja mai sus. Întreabă strict despre un aspect nou din: \"{next_topic}\".\n"
            anti_rep_en = f"\nSTRICT ANTI-REPETITION DIRECTIVE:\nPrevious questions:\n{formatted_qs}\n- Do NOT repeat concepts asked above. Switch to a new topic in: \"{next_topic}\".\n"

    if language == "ro":
        follow_up_hint = (
            "Formulează o întrebare tehnică aprofundată pe baza răspunsului candidatului."
            if is_follow_up
            else f"Treci direct la următoarea competență tehnică: \"{next_topic}\"."
        )
        return f"""Ești INTERVIEVATORUL TEHNIC (angajatorul) pentru rolul de {job_title} ({rubric['title']}).

Răspunsul oferit anterior de candidat ({candidate_name}):
\"{candidate_answer[:500]}\"

Competență tehnică vizată pentru următoarea întrebare: \"{next_topic}\"
{anti_rep_ro}
DIRECTIVĂ:
{follow_up_hint}

REGULI CRITICE (OBLIGATORII):
1. TU EȘTI EXCLUSIV INTERVIEVATORUL: Este STRICT INTERZIS să oferi soluții tehnice, să răspunzi la întrebare sau să vorbești din perspectiva 'Aș folosi...', 'Aș face...', 'Aplicația va...'. ROLUL TĂU ESTE DOAR SĂ PUI O NOUĂ ÎNTREBARE TEHNICĂ CĂTRE CANDIDAT.
2. FĂRĂ SALUTURI SAU RECAPITULĂRI: Nu saluta ('Salut', 'Bună') și nu rezuma ce a zis candidatul. Formulează direct întrebarea tehnică.
3. PERSOANA A II-A SINGULAR EXCLUSIV: Adresează-te candidatului cu 'tu' ('Cum ai gestiona...', 'Ce abordare ai alege...').
4. STRICT O SINGURĂ ÎNTREBARE TEHNICĂ: Output-ul tău trebuie să fie STRICT o întrebare tehnică care se termină obligatoriu cu semnul întrebării (?).
5. ZERO OBSERVAȚII SAU META-COMENTARII: Este STRICT INTERZIS să adaugi 'Observație:', 'Notă:', 'Explicație:' sau comentarii despre întrebare. Output-ul tău este doar textul întrebării."""
    else:
        follow_up_hint = (
            "Ask a focused follow-up technical question delving deeper into their answer."
            if is_follow_up
            else f"Transition directly to the next technical competency: \"{next_topic}\"."
        )
        return f"""You are the TECHNICAL INTERVIEWER (the employer) for {job_title} ({rubric['title']}).

Candidate Answer ({candidate_name}):
\"{candidate_answer[:500]}\"

Target Competency for next question: \"{next_topic}\"
{anti_rep_en}
DIRECTIVE:
{follow_up_hint}

CRITICAL RULES (MANDATORY):
1. YOU ARE STRICTLY THE INTERVIEWER: You are NEVER the candidate. It is STRICTLY FORBIDDEN to provide technical solutions or speak from candidate perspective (do NOT say 'I would use...', 'The app will...'). Your ONLY task is to ASK a new technical question.
2. NO GREETINGS OR RECAPS: Do not greet and do not summarize previous answers. Go straight to the technical question.
3. STRICT SINGLE QUESTION: Formulate strictly ONE practical technical question ending with a question mark (?).
4. ZERO META-OBSERVATIONS OR NOTES: It is STRICTLY FORBIDDEN to add 'Note:', 'Observation:', 'Explanation:' or commentary about the question. Output ONLY direct speech to the candidate."""

def build_conversation_summary_prompt(
    job_title: str,
    candidate_name: str,
    rounds_to_summarize: List[Dict[str, str]],
    existing_summary: Optional[str] = None,
) -> str:
    """Generate a dense, factual cumulative technical summary of earlier interview rounds."""
    rounds_text = []
    for idx, r in enumerate(rounds_to_summarize, 1):
        q = r.get("question", "").strip()
        a = r.get("answer", "").strip()
        rounds_text.append(f"Turn #{idx}:\n- Question asked: {q}\n- Candidate response: {a}")

    new_turns_block = "\n\n".join(rounds_text) if rounds_text else "No new turns to summarize."
    existing_block = (
        f"PREVIOUS CUMULATIVE SUMMARY (TO EXTEND & INTEGRATE):\n{existing_summary.strip()}\n\n"
        if existing_summary and existing_summary.strip()
        else ""
    )

    return f"""You are a Technical Interview Recorder updating the progressive summary of an ongoing interview.

Target Role: {job_title}
Candidate Name: {candidate_name}

{existing_block}NEW DIALOGUE TURNS TO INTEGRATE:
{new_turns_block}

INSTRUCTIONS:
Produce a concise, information-dense summary combining previous context with the new turns.
Include:
1. Competencies Evaluated: What topics were asked.
2. Candidate's Demonstrated Knowledge: Exact patterns, technologies, and depth demonstrated.
3. Candidate Gaps or Skips: Topics where the candidate admitted lack of experience or struggled.

CRITICAL RULES:
- Be strictly factual based on candidate's actual statements.
- Keep it under 250 words total.
- Output ONLY the summary text."""

def build_chunk_evaluation_prompt(
    job_title: str,
    job_description: str,
    experience_level: str,
    candidate_name: str,
    chunk_rounds: List[Dict[str, Any]],
    chunk_index: int = 1,
    total_chunks: int = 1,
) -> str:
    """Prompt to evaluate a slice of interview exchanges fairly against the JD and seniority level."""
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])

    qa_blocks = []
    for r in chunk_rounds:
        q = r.get("question", "").strip()
        a = r.get("answer", "").strip()
        qid = r.get("question_id", 1)
        qa_blocks.append(
            f"EXCHANGE ROUND #{qid}:\n"
            f"  [QUESTION ASKED BY INTERVIEWER]: \"{q}\"\n"
            f"  [CANDIDATE'S ACTUAL RESPONSE]: \"{a}\""
        )
    chunk_transcript = "\n\n".join(qa_blocks)

    return f"""You are a fair technical hiring committee member evaluating Chunk #{chunk_index} of {total_chunks} for {candidate_name} applying for {job_title} ({rubric['title']}).

Seniority Standard: {rubric['title']} ({rubric['focus']})
Role Requirements:
{job_description[:700]}

INTERVIEW EXCHANGES IN THIS CHUNK:
{chunk_transcript}

EVALUATION PRINCIPLES:
1. STRICT CLARIFICATION IMMUNITY: Distinguish between clarifications, questions asked by candidate, language switches, refusals ('nu stiu'), and actual answers.
   - Do NOT penalize the candidate for asking for clarification (e.g. asking about role seniority, scope, or tools).
   - NEVER put candidate questions or clarification inquiries into the weaknesses list.
   - Grade ONLY how well the candidate demonstrated technical competence when providing actual solutions.
2. For unanswered/skipped questions, note the gap objectively without malice.

OUTPUT FORMAT (valid JSON ONLY):
{{
  "chunk_index": {chunk_index},
  "chunk_score": <float 1.0 to 10.0 for this batch>,
  "question_evaluations": [
    {{
      "question_id": <int or str>,
      "question_text": "<summary of question asked>",
      "candidate_response": "<snippet of candidate answer>",
      "explanation": "<specific evaluation against seniority standard>",
      "score": <float 1.0 to 10.0>
    }}
  ]
}}"""

def build_final_evaluation_aggregation_prompt(
    job_title: str,
    job_description: str,
    experience_level: str,
    candidate_name: str,
    chunk_evaluations: List[Dict[str, Any]],
    topics_plan: Optional[List[str]] = None,
    time_limit_minutes: Optional[int] = None,
    covered_topics_count: Optional[int] = None,
    total_topics_count: Optional[int] = None,
) -> str:
    """Prompt to aggregate chunk evaluations into the unified final hiring report."""
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])

    chunk_summaries = []
    all_question_evals = []
    for ch in chunk_evaluations:
        c_idx = ch.get("chunk_index", 1)
        c_score = ch.get("chunk_score", 0.0)
        q_evals = ch.get("question_evaluations", [])
        all_question_evals.extend(q_evals)
        chunk_summaries.append(f"- Chunk #{c_idx}: Partial Score {c_score}/10 ({len(q_evals)} questions evaluated)")

    chunk_overview = "\n".join(chunk_summaries)
    question_evals_json = json.dumps(all_question_evals, indent=2, ensure_ascii=False)

    topics_summary = ""
    if topics_plan:
        covered = covered_topics_count or 0
        total = total_topics_count or len(topics_plan)
        topics_summary = (
            f"SESSION COVERAGE:\n"
            f"- Planned Topics ({total}): {', '.join(topics_plan)}\n"
            f"- Covered: {covered} of {total}\n"
            f"- Time Limit: {time_limit_minutes if time_limit_minutes else 'Untimed'} min\n\n"
        )

    return f"""You are the Senior Hiring Committee Chair synthesizing multi-chunk evaluations into a final, unified hiring decision for {candidate_name} applying for {job_title} ({rubric['title']}).

Seniority Standard: {rubric['title']} ({rubric['focus']})
Seniority Grading Rubric: {rubric['evaluation_standard']}

{topics_summary}CHUNK EVALUATION OVERVIEWS:
{chunk_overview}

DETAILED PER-QUESTION EVALUATIONS ACROSS ALL CHUNKS:
{question_evals_json}

SYNTHESIS INSTRUCTIONS:
1. Calculate overall weighted scores (1.0 to 10.0) based on all question evaluations.
2. Fair Grading: Differentiate between valid answers vs clarifications vs skips. Do not penalize candidate for asking clarification questions.
3. Strict Weakness Filtering: Exclude any candidate questions or inquiries from the weaknesses list. Include ONLY actual demonstrated technical gaps in candidate solutions.
4. Extract key strengths strictly if backed by candidate's actual demonstrated knowledge.

OUTPUT FORMAT (valid JSON ONLY):
{{
  "technical_score": <float between 1.0 and 10.0>,
  "communication_score": <float between 1.0 and 10.0>,
  "experience_score": <float between 1.0 and 10.0>,
  "overall_score": <float between 1.0 and 10.0>,
  "recommendation": <"strong_hire" | "hire" | "leaning_no_hire" | "no_hire">,
  "strengths": [<list of specific positive observations backed strictly by answers>],
  "weaknesses": [
    {{
      "question_id": <int or str>,
      "question_text": "<summary of question>",
      "response_text": "<snippet of candidate answer>",
      "explanation": "<specific hiring feedback on what was missing or why it fails role expectations>"
    }}
  ],
  "summary": "<concise 2-3 sentence honest hiring assessment of candidate's answers against {rubric['title']} level>"
}}"""

def is_wrapup_or_evaluation_message(content: str) -> bool:
    """Check if an assistant message is an interview closing/thank-you message rather than a technical question."""
    lower = content.lower().strip()
    if "[interview_complete]" in lower:
        return True
    if "**overall ai assessment:" in lower or "**evaluare generală ai:" in lower or "**evaluare generala ai:" in lower:
        return True

    closing_indicators = [
        r"\b(iti\s+multumesc|va\s+multumesc|iti\s+multumim|va\s+multumim|multumim|thank\s+you)\b",
        r"\b(interviul\s+(tehnic\s+)?s-?a\s+(incheiat|luat\s+sfarsit)|sesiunea\s+de\s+interviu\s+s-?a\s+(incheiat|luat\s+sfarsit)|interview\s+is\s+complete|interview\s+has\s+concluded)\b",
        r"\b(vom\s+reveni\s+cu\s+un\s+feedback|the\s+recruitment\s+team\s+will\s+review|transcrierea\s+a\s+fost\s+inregistrata|transcript\s+has\s+been\s+recorded)\b",
        r"\b(evaluare\s+generala|overall\s+ai\s+assessment|recruiter\s+evaluation|puncte\s+forte|arii\s+de\s+imbunatatire|key\s+strengths)\b",
    ]
    return any(re.search(pat, lower) for pat in closing_indicators)


def is_clarification_user_query(content: str) -> bool:
    """Check if a user message is an inquiry/clarification rather than a final substantive technical answer."""
    lower = content.lower().strip()
    replacements = {'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ş': 's', 'ț': 't', 'ţ': 't'}
    for k, v in replacements.items():
        lower = lower.replace(k, v)

    has_substantive = bool(re.search(
        r"\b(as\s+folosi|as\s+alege|as\s+face|as\s+implementa|as\s+crea|pentru\s+ca|deoarece|in\s+schimb|i\s+would|because|i\s+prefer|my\s+solution|implementing|using|solutia\s+mea)\b",
        lower
    )) and len(lower.split()) >= 15
    if has_substantive:
        return False

    clarification_patterns = [
        r"\b(nu\s+inteleg|nu\s+prea\s+inteleg|nu\s+am\s+inteles|i\s+don'?t\s+understand)\b",
        r"\b(poti\s+(sa\s+)?(clarifici|clarifica|reformulezi|detaliezi|explici)|could\s+you\s+(clarify|rephrase|explain)|can\s+you\s+(clarify|rephrase|explain))\b",
        r"\b(clarifica|clarificare|rephrase|clarify|detaliaza)\b",
        r"\b(nu\s+(imi\s+)?e(ste)?\s+(foarte\s+)?clar|it'?s\s+not\s+clear|not\s+very\s+clear|unclear)\b",
        r"\b(la\s+ce\s+te\s+referi|what\s+do\s+you\s+mean|what\s+does\s+that\s+mean|ce\s+vrei\s+sa\s+spui|ce\s+ai\s+vrea)\b",
        r"\b(ce\s+inseamna|ce\s+e\s+aia|ce\s+este|ce\s+reprezinta|what\s+is|what\s+does\s+.*\s+mean|what\s+are)\b",
        r"\b(te\s+referi\s+la|do\s+you\s+mean|ce\s+parte|care\s+dintre|sau\s+ambele|despre\s+ce|ce\s+anume)\b",
        r"\b(pot\s+folosi|pot\s+sa\s+folosesc|can\s+i\s+use|should\s+i\s+use|is\s+it\s+allowed|avem\s+voie)\b",
        r"\b(junior|mid|senior|lead|nivelul|standardul)\b",
    ]
    if any(re.search(pat, lower) for pat in clarification_patterns):
        return True
    if "?" in lower and not has_substantive:
        return True
    return False


def parse_transcript_into_qa_rounds(transcript: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Parse chronological transcript messages into cohesive structured Q&A rounds."""
    rounds: List[Dict[str, Any]] = []
    current_q: Optional[str] = None
    clarifications_for_current_q: List[str] = []
    round_idx = 1

    for msg in transcript:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        if not content:
            continue

        if role in ["assistant", "system"]:
            if is_wrapup_or_evaluation_message(content):
                continue

            if current_q is not None and clarifications_for_current_q:
                # Assistant clarifying in response to candidate's inquiry
                pass
            else:
                current_q = content
                clarifications_for_current_q = []

        elif role == "user":
            if current_q is not None:
                if is_clarification_user_query(content):
                    clarifications_for_current_q.append(content)
                else:
                    answer_text = content
                    if clarifications_for_current_q:
                        clarif_summary = "; ".join(f'"{c}"' for c in clarifications_for_current_q)
                        answer_text = f"{content}\n[Clarification Context: Candidate proactively clarified: {clarif_summary} prior to solving.]"

                    rounds.append({
                        "question_id": round_idx,
                        "question": current_q,
                        "answer": answer_text,
                    })
                    current_q = None
                    clarifications_for_current_q = []
                    round_idx += 1
            else:
                if rounds:
                    rounds[-1]["answer"] += f"\n[Additional Follow-up Response]: {content}"

    if current_q is not None and not is_wrapup_or_evaluation_message(current_q):
        if "?" in current_q and len(current_q.split()) > 6:
            rounds.append({
                "question_id": round_idx,
                "question": current_q,
                "answer": "[NO RESPONSE PROVIDED - CANDIDATE CONCLUDED SESSION WITHOUT ANSWERING]",
            })

    return rounds


def build_evaluation_report_prompt(
    job_title: str,
    job_description: str,
    candidate_name: str,
    cv_raw_text: str,
    transcript: List[Dict[str, str]],
    experience_level: str = "mid",
    time_limit_minutes: Optional[int] = None,
    covered_topics_count: Optional[int] = None,
    total_topics_count: Optional[int] = None,
    topics_plan: Optional[List[str]] = None,
) -> str:
    """Prompt to evaluate a standard-length interview transcript fairly."""
    rubric = SENIORITY_RUBRICS.get(experience_level.lower(), SENIORITY_RUBRICS["mid"])

    qa_rounds_struct = parse_transcript_into_qa_rounds(transcript)
    qa_rounds = []
    for r in qa_rounds_struct:
        qid = r.get("question_id", 1)
        q = r.get("question", "")
        a = r.get("answer", "")
        qa_rounds.append(
            f"EXCHANGE ROUND #{qid}:\n"
            f"  [QUESTION ASKED BY INTERVIEWER]: \"{q}\"\n"
            f"  [CANDIDATE'S ACTUAL RESPONSE]: \"{a}\"\n"
        )

    formatted_qa_transcript = "\n".join(qa_rounds) if qa_rounds else "No interview exchanges recorded."

    topics_summary = ""
    if topics_plan:
        covered = covered_topics_count or 0
        total = total_topics_count or len(topics_plan)
        topics_summary = (
            f"SESSION COVERAGE:\n"
            f"- Planned Technical Topics ({total}): {', '.join(topics_plan)}\n"
            f"- Actually Covered Topics: {covered} out of {total}\n"
            f"- Allocated Time Limit: {time_limit_minutes if time_limit_minutes else 'Untimed'} minutes\n\n"
        )

    return f"""You are a rigorous, fair Senior Hiring Committee Chair evaluating a completed technical interview.

Target Role: {job_title} ({rubric['title']})
Seniority Level Standard: {rubric['title']}
Seniority Evaluation Focus: {rubric['focus']}
Seniority Grading Rubric: {rubric['evaluation_standard']}

Role Requirements:
{job_description}

Candidate Name: {candidate_name}

{topics_summary}INTERVIEW TRANSCRIPT (STRUCTURED ROUNDS):
{formatted_qa_transcript}

EVALUATION PRINCIPLES:
1. STRICT CLARIFICATION IMMUNITY (CRITICAL):
   - Asking for clarification, asking questions about the role/seniority (e.g. "postul este de junior mid sau senior?", "pot folosi redis?", "ce inseamna X?"), or requesting details is a positive engineering practice.
   - NEVER classify clarification inquiries or questions asked by the candidate as a failed answer, gap, or weakness!
   - DO NOT list candidate questions or inquiries in the "weaknesses" table.
   - Grade the candidate strictly and exclusively on their actual proposed technical solutions and answers.
2. FAIR EVALUATION: Distinguish between:
   - Clarifying exchanges: Neutral/Positive. DO NOT penalize.
   - Language switches (e.g. candidate asks to speak in Romanian): Neutral. DO NOT penalize.
   - Refusals ('nu stiu', 'skip'): Record the competency gap factually.
   - Actual technical answers: Grade thoroughly against the {rubric['title']} standard.
3. ZERO-CREDIT FOR INTERVIEWER'S WORDS:
   - Concepts mentioned inside the interviewer's questions belong to the interviewer. Award credit only for what the candidate explained in their own words.

OUTPUT FORMAT:
Output MUST be valid JSON ONLY (no markdown backticks, no commentary) matching this exact schema:
{{
  "technical_score": <float between 1.0 and 10.0>,
  "communication_score": <float between 1.0 and 10.0>,
  "experience_score": <float between 1.0 and 10.0>,
  "overall_score": <float between 1.0 and 10.0>,
  "recommendation": <"strong_hire" | "hire" | "leaning_no_hire" | "no_hire">,
  "strengths": [
    <list of specific positive technical observations backed by candidate's actual answers>
  ],
  "weaknesses": [
    {{
      "question_id": 1,
      "question_text": "<summary of question asked>",
      "response_text": "<exact candidate response snippet>",
      "explanation": "<specific evaluation of what was missing or why this response fails role expectations>"
    }}
  ],
  "summary": "<concise 2-3 sentence honest hiring assessment of candidate's answers against {rubric['title']} level>"
}}
"""
