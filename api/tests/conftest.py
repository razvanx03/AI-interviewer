import sys
import uuid
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

# Add api to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main import app
from db.session import async_session_maker, get_db, db_url
from models.user import User
from models.interview import Interview
from core.security import get_password_hash, create_access_token
from services.interview_service import interview_service
from llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for unit and integration testing."""

    def __init__(self):
        self.last_prompt = ""
        self.calls = []

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        self.last_prompt = messages[-1]["content"] if messages else ""
        self.calls.append({"system_prompt": system_prompt, "messages": messages})
        content = self.last_prompt

        if "Target Topic for Question 1" in content or "Question 1" in content:
            return (
                "Salut Andrei! Mă bucur să ne cunoaștem la interviul pentru Backend Engineer. "
                "Pentru început, cum ai structura un modul de servicii într-o aplicație FastAPI?"
            )
        elif "screening_results" in content or "Senior Technical Recruiter screening" in content:
            return """{
              "screening_results": [
                {
                  "name": "Andrei Popescu",
                  "match_score": 9.2,
                  "strengths": ["FastAPI", "PostgreSQL", "Docker"],
                  "summary": "Strong engineering background with 4 years experience."
                }
              ]
            }"""
        elif "clarificare" in content.lower() or "clarification" in content.lower():
            return (
                "Un modul de servicii încapsulează logica de business independent de controllere. "
                "Revenind la întrebare: cum ai structura acest modul în FastAPI?"
            )
        elif "nu cunoaște" in content or "nu a lucrat" in content or "nu stiu" in content.lower():
            return (
                "Nicio problemă, e în regulă! Să trecem la următoarea temă: "
                "Cum optimizezi o interogare lentă în PostgreSQL?"
            )
        elif "INTERVIEW_COMPLETE" in content:
            return (
                "Îți mulțumesc pentru răspunsuri și pentru discuție! "
                "Interviul s-a încheiat. [INTERVIEW_COMPLETE]"
            )
        else:
            return (
                "Are sens abordarea ta. Trecând la următorul subiect: "
                "Cum gestionezi concurența și tranzacțiile în baza de date?"
            )

    async def generate_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ):
        resp = await self.generate_response(system_prompt, messages, temperature)
        words = resp.split(" ")
        for i, word in enumerate(words):
            suffix = " " if i < len(words) - 1 else ""
            yield word + suffix

    async def summarize_conversation_history(
        self,
        job_title: str,
        candidate_name: str,
        rounds_to_summarize: List[Dict[str, str]],
        existing_summary: str = None,
    ) -> str:
        return f"Cumulative summary for {candidate_name} across {len(rounds_to_summarize)} rounds."

    async def evaluate_interview(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return {
            "overall_score": 8.8,
            "technical_score": 8.5,
            "communication_score": 9.0,
            "experience_score": 8.5,
            "recommendation": "hire",
            "strengths": ["FastAPI architecture", "PostgreSQL indexing", "Clear communication"],
            "weaknesses": [
                {
                    "question_id": 2,
                    "question_text": "Microservices",
                    "response_text": "nu stiu",
                    "explanation": "Candidate has less experience in distributed tracing.",
                }
            ],
            "summary": "Candidate demonstrated strong engineering autonomy and clean design skills.",
        }


from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

test_engine = create_async_engine(
    db_url,
    poolclass=NullPool,
    echo=False,
    future=True,
)

test_session_maker = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session per test with clean commit/rollback."""
    async with test_session_maker() as session:
        yield session


@pytest.fixture(autouse=True)
def mock_interview_llm():
    """Inject MockLLM into interview_service for all tests."""
    mock = MockLLMProvider()
    original = interview_service.llm
    interview_service.llm = mock
    yield mock
    interview_service.llm = original


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client fixture with FastAPI app dependency overrides."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create or retrieve a standard admin test user in the database."""
    user_id = str(uuid.uuid4())[:8]
    user = User(
        id=user_id,
        email=f"testuser_{user_id}@example.com",
        hashed_password=get_password_hash("TestPassword123!"),
        full_name="Test Recruiter",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> Dict[str, str]:
    """Return valid Authorization Bearer header for test_user."""
    token = create_access_token(data={"sub": test_user.id, "email": test_user.email, "role": test_user.role})
    return {"Authorization": f"Bearer {token}"}
