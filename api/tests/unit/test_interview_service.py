import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.interview import InterviewCreate, ExperienceLevel, InterviewStatus
from services.interview_service import interview_service, _format_eval_feedback_section
from models.interview import Interview


class TestInterviewService:
    """Unit tests for interview lifecycle, state machine transitions, and evaluation."""

    async def test_create_interview_starts_with_question_1(self, db_session: AsyncSession):
        data = InterviewCreate(
            job_title="Senior Backend Engineer",
            company_name="Tech Solutions",
            job_description="We need a Python engineer with FastAPI, PostgreSQL, and Docker experience.",
            experience_level=ExperienceLevel.MID,
            candidate_name="Dariusbotezan2026",
            language="ro",
            time_limit_minutes=30,
        )
        interview = await interview_service.create_interview(db_session, data)

        try:
            assert interview.id is not None
            assert interview.job_title == "Senior Backend Engineer"
            assert interview.active_question_number == 1
            assert interview.active_question_status == "WAITING_ANSWER"
            assert interview.active_question_text is not None
            assert interview.consecutive_clarifications == 0
            assert len(interview.topics_plan) > 0
            assert len(interview.messages) == 1
            assert interview.messages[0].question_number == 1
        finally:
            await interview_service.delete_interview(db_session, interview.id)

    async def test_state_machine_answer_progression(self, db_session: AsyncSession):
        data = InterviewCreate(
            job_title="Full Stack Developer",
            company_name="Innovate Ltd",
            job_description="React, Node.js, and SQL.",
            experience_level=ExperienceLevel.MID,
            candidate_name="Alex",
            language="ro",
        )
        interview = await interview_service.create_interview(db_session, data)

        try:
            # Turn 1: Candidate answers Question 1
            res1 = await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "Pentru gestionarea starii as folosi React Context si useReducer pentru componentele partajate.",
            )
            assert res1.next_question_number == 2
            int1 = await interview_service.get_interview(db_session, interview.id)
            assert int1.active_question_number == 2
            assert int1.consecutive_clarifications == 0
            assert len(int1.assessed_topics) == 1

            # Turn 2: Candidate answers Question 2
            res2 = await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "Pentru API-uri in Node.js folosesc Express sau NestJS cu validare prin zod.",
            )
            assert res2.next_question_number == 3
            int2 = await interview_service.get_interview(db_session, interview.id)
            assert int2.active_question_number == 3
            assert len(int2.assessed_topics) == 2
        finally:
            await interview_service.delete_interview(db_session, interview.id)

    async def test_state_machine_clarification_handling(self, db_session: AsyncSession):
        data = InterviewCreate(
            job_title="Python Engineer",
            job_description="FastAPI, AsyncIO, PostgreSQL.",
            experience_level=ExperienceLevel.MID,
            candidate_name="Darius",
            language="ro",
        )
        interview = await interview_service.create_interview(db_session, data)

        try:
            # Turn 1: Candidate asks for clarification
            res1 = await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "Ce inseamna mai exact un context manager asincron?",
            )
            assert res1.next_question_number == 1
            int1 = await interview_service.get_interview(db_session, interview.id)
            assert int1.active_question_number == 1
            assert int1.consecutive_clarifications == 1

            # Turn 2: Second clarification
            res2 = await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "Poti reformula te rog cerinta?",
            )
            assert res2.next_question_number == 1
            int2 = await interview_service.get_interview(db_session, interview.id)
            assert int2.active_question_number == 1
            assert int2.consecutive_clarifications == 2

            # Turn 3: Candidate now provides an answer -> resets clarifications and advances
            res3 = await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "Un context manager asincron implementeaza __aenter__ si __aexit__ pentru resurse asincrone.",
            )
            assert res3.next_question_number == 2
            int3 = await interview_service.get_interview(db_session, interview.id)
            assert int3.active_question_number == 2
            assert int3.consecutive_clarifications == 0
            assert len(int3.assessed_topics) == 1
        finally:
            await interview_service.delete_interview(db_session, interview.id)

    async def test_state_machine_skip_and_refusal(self, db_session: AsyncSession):
        data = InterviewCreate(
            job_title="Backend Engineer",
            job_description="Python, PostgreSQL, RabbitMQ, Docker.",
            experience_level=ExperienceLevel.MID,
            candidate_name="Radu",
            language="ro",
        )
        interview = await interview_service.create_interview(db_session, data)

        try:
            # Candidate skips Question 1
            res = await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "Nu stiu, nu am lucrat cu tehnologia asta niciodata",
            )
            assert res.next_question_number == 2
            int_obj = await interview_service.get_interview(db_session, interview.id)
            assert int_obj.active_question_number == 2
            assert int_obj.consecutive_clarifications == 0
        finally:
            await interview_service.delete_interview(db_session, interview.id)

    async def test_state_machine_language_switch(self, db_session: AsyncSession):
        data = InterviewCreate(
            job_title="Backend Engineer",
            job_description="Python and SQL.",
            experience_level=ExperienceLevel.MID,
            candidate_name="Elena",
            language="en",
        )
        interview = await interview_service.create_interview(db_session, data)

        try:
            # Candidate asks to switch to Romanian
            res = await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "Putem continua in limba romana te rog?",
            )
            assert res.next_question_number == 1
            int_obj = await interview_service.get_interview(db_session, interview.id)
            assert int_obj.language == "ro"
            assert int_obj.active_question_number == 1
        finally:
            await interview_service.delete_interview(db_session, interview.id)

    async def test_complete_interview_and_evaluation(self, db_session: AsyncSession):
        data = InterviewCreate(
            job_title="Senior Python Architect",
            job_description="Architecture, FastAPI, PostgreSQL.",
            experience_level=ExperienceLevel.SENIOR,
            candidate_name="Andrei",
            language="en",
        )
        interview = await interview_service.create_interview(db_session, data)

        try:
            # Add an answer message
            await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "I use hexagonal architecture to decouple domain logic from database and transport adapters.",
            )

            # Complete interview
            completed = await interview_service.complete_interview(db_session, interview.id)
            assert completed.status == InterviewStatus.COMPLETED
            messages = await interview_service.get_messages(db_session, interview.id)
            assert len(messages) >= 2
            last_msg = messages[-1]
            assert last_msg.role.value == "assistant"
        finally:
            await interview_service.delete_interview(db_session, interview.id)

    @pytest.mark.asyncio
    async def test_early_finish_coverage_weighting_and_unassessed_topics(
        self, db_session: AsyncSession
    ):
        """Verify that early termination with partial topic coverage scales down score and lists unassessed topics."""
        # Create an interview with 9 planned topics
        req = InterviewCreate(
            job_title="Backend Engineer",
            job_description=(
                "- RESTful API and microservices architecture\n"
                "- PostgreSQL, database indexing, and query optimization\n"
                "- Redis caching and pub/sub messaging\n"
                "- Distributed tracing and observability with Prometheus\n"
                "- Background job processing with Celery or RabbitMQ\n"
                "- Docker, containerization, and Kubernetes\n"
                "- Security, OAuth2, and PCI-DSS compliance\n"
                "- Automated testing with PyTest and CI/CD pipelines\n"
                "- Concurrency, async programming, and system resilience\n"
            ),
            candidate_name="Test Candidate",
            experience_level=ExperienceLevel.MID,
            time_limit_minutes=None,  # Untimed (defaults to 7 topics)
        )
        interview = await interview_service.create_interview(db_session, req)
        try:
            assert len(interview.topics_plan) == 7

            # Answer Question 1
            await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "I would design a stateless REST API with FastAPI and connection pooling.",
            )

            # Answer Question 2
            await interview_service.add_candidate_message_and_respond(
                db_session,
                interview.id,
                "I use PostgreSQL with composite indexes and explain analyze to profile queries.",
            )

            # Now early finish before answering Question 3 or the rest of the 7 topics
            completed = await interview_service.complete_interview(
                db=db_session, interview_id=interview.id
            )
            assert completed.status == InterviewStatus.COMPLETED

            messages = await interview_service.get_messages(db_session, interview.id)
            report_msg = messages[-1].content

            # Evaluated score should reflect coverage penalty (2/7 coverage ~ 28%)
            # Even if raw score from MockLLM was 8.8, 8.8 * (2/9) ~ 2.0 / 10
            assert "Evaluare Generală AI:" in report_msg or "Overall AI Assessment:" in report_msg
            assert "No Hire" in report_msg
            # Unassessed topics must be listed
            assert "Neevaluat - Sesiune finalizată" in report_msg or "Unassessed - Session Concluded" in report_msg
            assert "Acoperire Sesiune:" in report_msg or "Session Coverage:" in report_msg
        finally:
            await interview_service.delete_interview(db_session, interview.id)

    def test_format_eval_feedback_recovers_from_qa_rounds_map_with_fallback_qid(self):
        """When question_id is missing or non-numeric, qid falls back to idx and recovers text from qa_rounds_map."""
        qa_rounds_map = {
            1: {
                "question": "Explain ACID properties in PostgreSQL.",
                "answer": "Atomicity, Consistency, Isolation, and Durability guarantee reliable transactions.",
            }
        }
        # Item with no question_id and empty question_text/response_text
        items = [
            {
                "question_text": "",
                "response_text": "",
                "explanation": "Solid understanding of transactions.",
            }
        ]
        result = _format_eval_feedback_section(items, is_ro=False, qa_rounds_map=qa_rounds_map)
        assert "Explain ACID properties" in result
        assert "Atomicity, Consistency, Isolation" in result

    @pytest.mark.asyncio
    async def test_coverage_under_50_percent_caps_overall_score_at_4_5(
        self, db_session: AsyncSession
    ):
        """When coverage_ratio < 0.50, overall_score MUST NOT exceed 4.5/10."""
        req = InterviewCreate(
            job_title="Senior Python Architect",
            job_description="\n".join([f"- Competency {i}" for i in range(1, 11)]),
            candidate_name="High Scoring Candidate",
            experience_level=ExperienceLevel.SENIOR,
            time_limit_minutes=None,
        )
        interview = await interview_service.create_interview(db_session, req)
        try:
            # Answer 3 out of 7 topics (42.8% coverage < 50%)
            for i in range(1, 4):
                await interview_service.add_candidate_message_and_respond(
                    db_session,
                    interview.id,
                    f"Thorough architectural answer for topic {i} with design patterns and scaling principles.",
                )

            completed = await interview_service.complete_interview(
                db=db_session, interview_id=interview.id
            )
            assert completed.status == InterviewStatus.COMPLETED
            messages = await interview_service.get_messages(db_session, interview.id)
            report = messages[-1].content
            assert "No Hire" in report
            import re
            m = re.search(r'(?:Overall AI Assessment|Evaluare Generală AI):\s*([\d\.]+)/10', report)
            assert m is not None
            score = float(m.group(1))
            assert score <= 4.5
        finally:
            await interview_service.delete_interview(db_session, interview.id)
