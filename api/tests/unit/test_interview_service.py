import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.interview import InterviewCreate, ExperienceLevel, InterviewStatus
from services.interview_service import interview_service
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
