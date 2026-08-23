# Prompt Engineering (`llm/prompts.py`)

Defines system prompt templates, dynamic prompt builders, intent classifications, and completion protocols for the technical interview lifecycle.

---

## 1. `build_system_interviewer_prompt`

Assembles the real-time system prompt defining the AI Interviewer persona and dynamic state machine rules:
- **Inputs**: `job_title`, `job_description`, `experience_level`, `cv_raw_text`, `candidate_name`, `active_question_number`, `consecutive_clarifications`, `clarification_threshold`.
- **Assessment Checklist**: Mandates probing 5 key competency areas (Core Language/Framework, Architecture & Scalability, Database Performance, CV Project Deep-Dives, Problem-Solving & Edge Cases).
- **Conversational Protocol & Intent Handling**:
  - `[ANSWER]`: Candidate answered the active question $\rightarrow$ Evaluate depth and transition to the next checklist topic.
  - `[I DON'T KNOW / SKIP]`: Candidate indicates lack of knowledge or passes $\rightarrow$ Acknowledge politely without condescension and immediately pivot to a fresh checklist competency (e.g. Database Engineering, Query Performance) without repeating questions.
  - `[QUESTION / CLARIFICATION]`: Candidate asked for details $\rightarrow$ Answer concisely (1-2 sentences) and immediately re-steer back to the active problem without advancing question count.
  - `[BOTH]`: Address clarification and evaluate provided partial answer.
- **Anti-Repetition Directive**: Strict prohibition against repeating previous questions, scenarios, or robotic boilerplate phrases.
- **Autonomous Completion Protocol**: Emits `[INTERVIEW_COMPLETE]` once checklist competencies have sufficient evaluation evidence.
- **Multilingual & Dynamic Language Adaptability**: Continuously monitors the language used by the candidate (e.g. Romanian, English, French, Spanish, German). If the candidate speaks or switches to another language, the interviewer immediately mirrors that language for all subsequent dialogue while preserving standard software engineering terminology in English.
- **Dynamic Steering Directive**: Injected if consecutive candidate counter-questions exceed the steering threshold (3), prompting a firm but polite return to the active question.

---

## 2. `build_intro_question_prompt`

Generates the initial greeting and opening technical question tailored to the candidate's CV highlights when the interview session is created.

---

## 3. `build_evaluation_report_prompt`

Formats the entire completed interview transcript with candidate CV and job requirements to generate a structured JSON evaluation report (`technical_score`, `communication_score`, `experience_score`, `overall_score`, `recommendation`, `strengths`, `weaknesses`, `summary`).
- **Scoring Rubric & Grading Scale**: 1.0 - 10.0 scale with penalties for evasiveness/premature exit.
- **Retroactive / Delayed Answers Protocol**: If the candidate skipped a question initially but later returned with a valid technical explanation, partial credit (60-75%) is awarded to recognize their ultimate understanding while factoring in the delay.
