from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict

class InterviewState(TypedDict, total=False):
    """
    Central state schema representing the complete context of an ongoing technical interview
    orchestrated through a LangGraph StateGraph.
    """
    # Context and job metadata
    interview_id: str
    job_title: str
    company_name: Optional[str]
    job_description: str
    experience_level: str
    candidate_name: str
    language: str  # "ro" | "en"
    conversation_summary: Optional[str]

    # Topic plan and progression
    topics_plan: List[str]
    current_topic_index: int
    assessed_topics: List[str]
    topic_follow_up_count: int

    # Active question tracking
    active_question_number: int
    active_question_text: Optional[str]
    active_question_status: str
    consecutive_clarifications: int

    # Timing constraints
    time_limit_minutes: Optional[int]
    remaining_minutes: Optional[float]
    time_expired: bool

    # Turn execution
    candidate_message: str
    assistant_response: str
    intent: str
    needs_follow_up: bool
    is_complete: bool
    turn_prompt: str
    assigned_q_num: Optional[int]


    # Conversation history & anti-repetition
    previous_questions: List[str]

    # Final evaluation
    evaluation_report: Optional[Dict[str, Any]]

