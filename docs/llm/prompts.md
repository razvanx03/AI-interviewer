# Prompt Engineering (`llm/prompts.py`)

Defines modular system prompt templates, dynamic prompt builders, intent classifications, and completion protocols optimized for local LLMs (Qwen 3.5 8B) under deterministic backend state machine orchestration.

---

## 1. `build_system_interviewer_prompt`

Assembles the real-time system prompt defining the AI Interviewer persona and dynamic state machine rules:
- **Inputs**: `job_title`, `job_description`, `experience_level`, `company_name`, `cv_raw_text`, `candidate_name`, `target_language`, `conversation_summary`.
- **Seniority Rubrics**: Injects tailored focus and standards (`entry`, `mid`, `senior`, `lead`, `executive`).
- **Strict Single Question Principle**: Enforces strictly ONE technical question per turn without headers or bulleted lists.
- **Tone & Pronouns (Persoana a II-a Singular - Collegial & Respectful)**:
  - Adresează-te mereu la **persoana a II-a singular** (*„tu”*, *„cum ai gestiona”*, *„ce ai alege”*, *„cum vezi”*).
  - Interzice strict formele de politețe plural (*„dumneavoastră”*, *„vă rugăm”*, *„ați înțeles”*) și formele de persoana a III-a (*„ar lua”*).
  - Interzice prefixele vocative repetitive de tipul *„Spune-mi [Nume]”* sau repetarea numelui candidatului la fiecare turn. Întrebările încep direct și cu formulări variate.
- **Language Directives**: Full Romanian (`ro`) or English (`en`) mirroring while preserving technical terms (Docker, Redis, React, FastAPI, hook, state, etc.).
- **Prior Conversation Summary**: Injects dense progressive summaries of older rounds when context window threshold is reached.

---

## 2. Dynamic Turn Prompt Builders

### `build_intro_prompt`
- **Step 1 of Two-Step Intro**: Generates a warm, professional greeting and format overview, asking the candidate if they are ready to begin without asking technical questions yet.

### `build_first_question_prompt`
- **Step 2 of Two-Step Intro**: Acknowledges candidate readiness and poses Question 1 exploring the first core competency extracted from the Job Description.

### `build_clarification_response_prompt`
- Explains the requested term, concept, or constraint concisely (1-2 sentences) and smoothly returns to the **active question** (`active_question_text`).
- If `consecutive_clarifications >= 3`, politely states that candidate's technical problem-solving reasoning is needed to evaluate the role.

### `build_both_response_prompt`
- Addresses candidate's clarifying question briefly, acknowledges their partial answer, and asks the next question on `next_topic`.

### `build_refusal_response_prompt`
- Acknowledges supportively in 1 sentence when a candidate says "I don't know / haven't worked with this / skip", and transitions to `next_topic`.

### `build_next_question_prompt`
- Acknowledges candidate's answer and asks the next question on `next_topic`.
- Enforces a strict, absolute anti-repetition mandate prohibiting the re-asking or rephrasing of previous questions or `last_question`.
- When `is_final_wrap_up=True`: Generates a concise closing thank-you message and emits `[INTERVIEW_COMPLETE]`. Explicitly prohibits inviting the candidate to ask further questions or reply since the chat terminates immediately.

---

## 3. Evaluation and Extraction Builders

- **`build_extract_topics_prompt`**: Extracts 4-6 realistic, core technical competencies directly from the Job Description and seniority level.
- **`build_screening_prompt`**: Scores and ranks multi-candidate CV pools against Job Description.
- **`build_conversation_summary_prompt`**: Generates dense progressive summaries for context window management.
- **`parse_transcript_into_qa_rounds`**: Robust transcript parser that intelligently merges clarification inquiries into parent technical questions and ignores closing thank-you turns, preventing ghost questions and artificial grading penalties.
- **`build_chunk_evaluation_prompt` & `build_final_evaluation_aggregation_prompt`**: Map-Reduce chunked evaluation for long sessions. Enforces symmetric structured schemas for both `strengths` and `weaknesses` with explicit `question_id`, `question_text`, `response_text`, and `explanation` fields. Injects session coverage metrics and enforces strict coverage penalties for early session conclusion.
- **`build_evaluation_report_prompt`**: Fair single-pass evaluation distinguishing clarifications, language switches, refusals, and substantive answers with structured `strengths` and `weaknesses` dictionaries. Enforces mandatory session coverage evaluation and early termination score bounding while guaranteeing immunity for administrative language switches.

