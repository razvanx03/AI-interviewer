import pytest
from httpx import AsyncClient
from models.user import User


class TestAPIEndpointsIntegration:
    """End-to-end integration tests for all FastAPI REST endpoints."""

    # --------------------------------------------------------------------------
    # Authentication Endpoints
    # --------------------------------------------------------------------------
    async def test_auth_login_success(self, async_client: AsyncClient, test_user: User):
        payload = {
            "username_or_email": test_user.email,
            "password": "TestPassword123!",
        }
        res = await async_client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email

    async def test_auth_login_invalid_password(self, async_client: AsyncClient, test_user: User):
        payload = {
            "username_or_email": test_user.email,
            "password": "WrongPassword123!",
        }
        res = await async_client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 401

    async def test_auth_get_me_authenticated(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        res = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    async def test_auth_get_me_unauthenticated(self, async_client: AsyncClient):
        res = await async_client.get("/api/v1/auth/me")
        assert res.status_code == 401

    async def test_auth_logout(self, async_client: AsyncClient):
        res = await async_client.post("/api/v1/auth/logout")
        assert res.status_code == 200

    # --------------------------------------------------------------------------
    # Screening Endpoint
    # --------------------------------------------------------------------------
    async def test_screen_candidates(self, async_client: AsyncClient, auth_headers: dict):
        payload = {
            "job_title": "Full Stack Engineer",
            "job_description": "React, TypeScript, FastAPI",
            "experience_level": "mid",
            "candidates": [
                {
                    "name": "Candidate Alpha",
                    "cv_raw_text": "3 years React, TypeScript, and FastAPI.",
                },
                {
                    "name": "Candidate Beta",
                    "cv_raw_text": "1 year PHP and WordPress.",
                },
            ],
        }
        res = await async_client.post("/api/v1/interviews/screen", json=payload, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "top_candidate" in data
        assert "screening_results" in data
        assert len(data["screening_results"]) == 2

    # --------------------------------------------------------------------------
    # Interview Lifecycle Endpoints
    # --------------------------------------------------------------------------
    async def test_interview_full_lifecycle_api(self, async_client: AsyncClient, auth_headers: dict):
        # 1. Create Interview
        create_payload = {
            "job_title": "Backend Developer",
            "company_name": "API Testing Inc",
            "job_description": "Python, FastAPI, and PostgreSQL development.",
            "experience_level": "mid",
            "candidate_name": "Darius",
            "language": "ro",
            "time_limit_minutes": 25,
        }
        create_res = await async_client.post("/api/v1/interviews", json=create_payload, headers=auth_headers)
        assert create_res.status_code == 201
        interview = create_res.json()
        interview_id = interview["id"]
        assert interview["status"] == "active"
        assert interview["active_question_number"] == 1
        assert interview["active_question_status"] == "WAITING_ANSWER"

        # 2. Get Interview Details
        get_res = await async_client.get(f"/api/v1/interviews/{interview_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == interview_id

        # 3. List Interviews
        list_res = await async_client.get("/api/v1/interviews", headers=auth_headers)
        assert list_res.status_code == 200
        interviews_list = list_res.json()
        assert any(i["id"] == interview_id for i in interviews_list)

        # 4. Get Messages
        msg_res = await async_client.get(f"/api/v1/interviews/{interview_id}/messages")
        assert msg_res.status_code == 200
        messages = msg_res.json()
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"

        # 5. Send Chat Message (Turn)
        chat_payload = {"content": "Folosesc dependency injection prin Depends() pentru a injecta sesiunea db."}
        chat_res = await async_client.post(f"/api/v1/interviews/{interview_id}/chat", json=chat_payload)
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "message" in chat_data
        assert chat_data["next_question_number"] == 2

        # 6. Stream Chat Message (SSE)
        stream_payload = {"content": "Optimizez interogarile folosind indecsi partiali si analizand planul de executie."}
        stream_res = await async_client.post(f"/api/v1/interviews/{interview_id}/stream", json=stream_payload)
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers.get("content-type", "")

        # 7. Complete Interview
        comp_res = await async_client.post(f"/api/v1/interviews/{interview_id}/complete")
        assert comp_res.status_code == 200
        assert comp_res.json()["status"] == "completed"

        # 8. Delete Interview
        del_res = await async_client.delete(f"/api/v1/interviews/{interview_id}", headers=auth_headers)
        assert del_res.status_code == 204
