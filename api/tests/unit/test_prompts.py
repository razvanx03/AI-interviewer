import pytest
from llm.prompts import (
    SENIORITY_RUBRICS,
    build_system_interviewer_prompt,
    build_first_question_prompt,
    build_clarification_response_prompt,
    build_both_response_prompt,
    build_refusal_response_prompt,
    build_next_question_prompt,
    build_extract_topics_prompt,
    build_screening_prompt,
    build_conversation_summary_prompt,
    build_chunk_evaluation_prompt,
    build_final_evaluation_aggregation_prompt,
    build_evaluation_report_prompt,
    parse_transcript_into_qa_rounds,
)


class TestPromptEngineering:
    """Comprehensive unit tests for modular prompt builders and seniority rubrics."""

    def test_seniority_rubrics_completeness(self):
        expected_levels = ["entry", "mid", "senior", "lead", "executive"]
        for level in expected_levels:
            assert level in SENIORITY_RUBRICS
            rubric = SENIORITY_RUBRICS[level]
            assert "title" in rubric
            assert "focus" in rubric
            assert "question_style" in rubric
            assert "evaluation_standard" in rubric

    def test_build_system_interviewer_prompt_romanian(self):
        prompt = build_system_interviewer_prompt(
            job_title="Backend Engineer",
            job_description="FastAPI, PostgreSQL, Redis",
            experience_level="mid",
            company_name="TechCorp",
            cv_raw_text="Experienced developer with 3 years Python.",
            candidate_name="Darius",
            target_language="ro",
        )
        assert "Backend Engineer" in prompt
        assert "TechCorp" in prompt
        assert "Darius" in prompt
        assert "PERSOANA A II-A SINGULAR" in prompt
        assert "STRICT PRONOUN RULE" in prompt
        assert "FastAPI, PostgreSQL, Redis" in prompt

    def test_build_system_interviewer_prompt_with_summary(self):
        prompt = build_system_interviewer_prompt(
            job_title="Frontend Developer",
            job_description="React, TypeScript",
            experience_level="senior",
            candidate_name="Elena",
            target_language="en",
            conversation_summary="Candidate previously explained React Fiber reconciliation.",
        )
        assert "Candidate previously explained React Fiber reconciliation." in prompt
        assert "PRIOR CONVERSATION SUMMARY" in prompt

    def test_build_first_question_prompt_romanian(self):
        prompt = build_first_question_prompt(
            job_title="Full Stack Engineer",
            job_description="React and Python",
            experience_level="mid",
            first_topic="React State Management",
            candidate_name="Darius",
            company_name="Google",
            language="ro",
        )
        assert "Darius" in prompt
        assert "React State Management" in prompt
        assert "persoana a II-a singular" in prompt
        assert "Google" in prompt
        assert "ONE clear question" in prompt

    def test_build_first_question_prompt_english(self):
        prompt = build_first_question_prompt(
            job_title="Backend Developer",
            job_description="Python, PostgreSQL",
            experience_level="senior",
            first_topic="Database Indexing & Query Plans",
            candidate_name="Alex",
            company_name="Acme Corp",
            language="en",
        )
        assert "Alex" in prompt
        assert "Database Indexing & Query Plans" in prompt
        assert "Acme Corp" in prompt
        assert "ENGLISH" in prompt

    def test_build_clarification_response_prompt_standard(self):
        prompt = build_clarification_response_prompt(
            job_title="Backend Engineer",
            experience_level="mid",
            candidate_name="Darius",
            active_question_text="Cum optimizezi un query cu JOIN pe 3 tabele?",
            candidate_query="Ce fel de indexuri avem pe foreign keys?",
            consecutive_clarifications=1,
            clarification_threshold=3,
            language="ro",
        )
        assert "Cum optimizezi un query cu JOIN pe 3 tabele?" in prompt
        assert "Ce fel de indexuri avem pe foreign keys?" in prompt
        assert "PERSOANA A II-A SINGULAR" in prompt
        assert "Rămâi pe aceeași întrebare activă" in prompt

    def test_build_clarification_response_prompt_threshold_reached(self):
        prompt = build_clarification_response_prompt(
            job_title="Backend Engineer",
            experience_level="mid",
            candidate_name="Darius",
            active_question_text="Cum optimizezi un query cu JOIN pe 3 tabele?",
            candidate_query="Poti sa imi mai dai un indiciu?",
            consecutive_clarifications=3,
            clarification_threshold=3,
            language="ro",
        )
        assert "Candidatul a cerut mai multe clarificări consecutive" in prompt
        assert "întrebarea activă" in prompt

    def test_build_both_response_prompt(self):
        prompt = build_both_response_prompt(
            job_title="DevOps Engineer",
            experience_level="senior",
            candidate_name="Mihai",
            active_question_text="Cum configurezi CI/CD pentru Kubernetes?",
            candidate_content="Pot folosi Helm? Si as adauga un pipeline in GitHub Actions cu caching.",
            next_topic="Monitoring & Prometheus Alerting",
            language="ro",
        )
        assert "Monitoring & Prometheus Alerting" in prompt
        assert "Pot folosi Helm?" in prompt
        assert "persoana a ii-a singular" in prompt.lower()

    def test_build_refusal_response_prompt(self):
        prompt = build_refusal_response_prompt(
            job_title="Backend Developer",
            experience_level="mid",
            candidate_name="Andrei",
            skipped_topic="Kafka & Event Sourcing",
            next_topic="PostgreSQL Performance",
            language="ro",
        )
        assert "Kafka & Event Sourcing" in prompt
        assert "PostgreSQL Performance" in prompt
        assert "persoana a ii-a singular" in prompt.lower()

    def test_build_next_question_prompt_turn_progression(self):
        prompt = build_next_question_prompt(
            job_title="Backend Engineer",
            experience_level="mid",
            candidate_name="Darius",
            last_question="Cum gestionezi migrarile in Alembic?",
            candidate_answer="Folosesc alembic revision --autogenerate si verific manual scriptul SQL.",
            next_topic="API Security & JWT",
            is_follow_up=False,
            language="ro",
            is_final_wrap_up=False,
        )
        assert "API Security & JWT" in prompt
        assert "Darius" in prompt
        assert "PERSOANA A II-A SINGULAR" in prompt

    def test_build_next_question_prompt_final_wrap_up(self):
        prompt = build_next_question_prompt(
            job_title="Backend Engineer",
            experience_level="mid",
            candidate_name="Darius",
            last_question="Cum gestionezi migrarile in Alembic?",
            candidate_answer="Am rulat migrarea cu succes.",
            next_topic="",
            language="ro",
            is_final_wrap_up=True,
        )
        assert "[INTERVIEW_COMPLETE]" in prompt
        assert "încheiat complet" in prompt
        assert "ESTE STRICT INTERZIS" in prompt

    def test_build_extract_topics_prompt(self):
        prompt = build_extract_topics_prompt(
            job_title="Senior Python Engineer",
            job_description="We need FastAPI, Docker, Microservices, and SQL optimization.",
            experience_level="senior",
        )
        assert "Senior Python Engineer" in prompt
        assert "Competency" in prompt
        assert "JSON ONLY" in prompt

    def test_build_screening_prompt(self):
        candidates = [
            {"name": "Candidate A", "cv_raw_text": "3 years Python and Django."},
            {"name": "Candidate B", "cv_raw_text": "5 years FastAPI and Kubernetes."},
        ]
        prompt = build_screening_prompt(
            job_title="Python Engineer",
            job_description="FastAPI and Docker",
            experience_level="mid",
            candidates=candidates,
        )
        assert "Candidate A" in prompt
        assert "Candidate B" in prompt
        assert "screening_results" in prompt

    def test_build_conversation_summary_prompt(self):
        rounds = [
            {"question": "How do you use Redis?", "answer": "As an LRU cache."},
            {"question": "How do you invalidate cache?", "answer": "Using TTL and event triggers."},
        ]
        prompt = build_conversation_summary_prompt(
            job_title="Backend Engineer",
            candidate_name="Alex",
            rounds_to_summarize=rounds,
        )
        assert "As an LRU cache" in prompt
        assert "Alex" in prompt

    def test_build_evaluation_report_prompt(self):
        messages = [
            {"role": "assistant", "content": "What is dependency injection in FastAPI?"},
            {"role": "user", "content": "It allows declaring dependencies via Depends()."},
        ]
        prompt = build_evaluation_report_prompt(
            job_title="Backend Engineer",
            job_description="FastAPI expertise",
            candidate_name="Alex",
            cv_raw_text="3 years FastAPI",
            transcript=messages,
            experience_level="mid",
        )
        assert "Depends()" in prompt
        assert "Alex" in prompt
        assert "recommendation" in prompt

    def test_parse_transcript_into_qa_rounds_with_clarifications(self):
        messages = [
            {"role": "assistant", "content": "Cum ai gestiona consistența datelor într-un sistem distribuit?"},
            {"role": "user", "content": "Poți clarifica puțin întrebarea? La ce aspect te referi?"},
            {"role": "assistant", "content": "Mă refer la gestionarea evenimentelor. Cum ai aborda tu problema?"},
            {"role": "user", "content": "Aș folosi evenimentele ca sursă de adevăr și aș face procesarea idempotentă."},
            {"role": "assistant", "content": "Îți mulțumesc pentru răspunsuri! [INTERVIEW_COMPLETE]"},
        ]
        rounds = parse_transcript_into_qa_rounds(messages)
        assert len(rounds) == 1
        assert rounds[0]["question"] == "Cum ai gestiona consistența datelor într-un sistem distribuit?"
        assert "procesarea idempotentă" in rounds[0]["answer"]
        assert "Clarification Context: Candidate proactively clarified" in rounds[0]["answer"]
