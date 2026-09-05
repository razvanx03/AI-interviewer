import pytest
from llm.agent import interview_graph, InterviewState

class TestInterviewStateGraph:
    """
    Unit test suite verifying the conversational interview workflow orchestrated by LangGraph StateGraph.
    """

    def test_start_interview_workflow(self):
        initial_state: InterviewState = {
            "candidate_message": "Salut, sunt gata să începem!",
            "active_question_status": "WAITING_GREETING",
            "job_title": "Senior Python Developer",
            "experience_level": "senior",
            "candidate_name": "Radu Ionescu",
            "language": "ro",
            "topics_plan": ["FastAPI & Async", "Database Indexing", "System Architecture"],
            "current_topic_index": 0,
            "active_question_number": 1,
        }

        output = interview_graph.invoke(initial_state)

        assert output.get("active_question_number") == 1
        assert output.get("active_question_status") == "WAITING_ANSWER"
        assert output.get("turn_prompt") is not None
        assert "Radu Ionescu" in output["turn_prompt"]
        assert "FastAPI & Async" in output["turn_prompt"]
        assert output.get("is_complete") is False

    def test_detect_clarification_workflow(self):
        state: InterviewState = {
            "candidate_message": "Ce anume înțelegi prin consistență eventuală în acest context?",
            "active_question_status": "WAITING_ANSWER",
            "active_question_number": 2,
            "active_question_text": "Cum gestionezi tranzacțiile distribuite într-o arhitectură de microservicii?",
            "job_title": "Backend Architect",
            "experience_level": "senior",
            "candidate_name": "Elena Popa",
            "language": "ro",
            "consecutive_clarifications": 0,
            "topics_plan": ["Microservices", "Event Sourcing"],
            "current_topic_index": 0,
        }

        output = interview_graph.invoke(state)

        assert output.get("intent") == "CLARIFICATION"
        assert output.get("consecutive_clarifications") == 1
        assert output.get("turn_prompt") is not None
        assert "Elena Popa" in output["turn_prompt"]
        assert output.get("assigned_q_num") == 2
        assert output.get("is_complete") is False

    def test_detect_refusal_skip_workflow(self):
        state: InterviewState = {
            "candidate_message": "Nu știu să răspund la asta, nu am lucrat cu Kafka, putem trece mai departe?",
            "active_question_status": "WAITING_ANSWER",
            "active_question_number": 2,
            "active_question_text": "Explică cum funcționează log compaction în Apache Kafka.",
            "job_title": "Data Platform Engineer",
            "experience_level": "mid",
            "candidate_name": "Andrei Mureșan",
            "language": "ro",
            "consecutive_clarifications": 1,
            "topics_plan": ["Kafka Internals", "PostgreSQL Sharding", "Redis Caching"],
            "current_topic_index": 0,
        }

        output = interview_graph.invoke(state)

        assert output.get("intent") == "REFUSAL"
        assert output.get("consecutive_clarifications") == 0
        assert output.get("current_topic_index") == 1
        assert output.get("active_question_number") == 3
        assert output.get("assigned_q_num") == 3
        assert "PostgreSQL Sharding" in output.get("turn_prompt", "")
        assert output.get("is_complete") is False

    def test_evaluate_answer_and_follow_up_workflow(self):
        # Short / shallow technical answer triggers follow-up
        state: InterviewState = {
            "candidate_message": "Aș folosi un index B-Tree.",
            "active_question_status": "WAITING_ANSWER",
            "active_question_number": 1,
            "active_question_text": "Cum optimizezi o interogare lentă într-o tabelă cu 10 milioane de înregistrări?",
            "job_title": "Database Engineer",
            "experience_level": "mid",
            "candidate_name": "Cristian Albu",
            "language": "ro",
            "topic_follow_up_count": 0,
            "topics_plan": ["Database Indexing", "Connection Pooling"],
            "current_topic_index": 0,
        }

        output = interview_graph.invoke(state)

        assert output.get("intent") == "ANSWER"
        assert output.get("needs_follow_up") is True
        assert output.get("topic_follow_up_count") == 1
        assert output.get("active_question_number") == 2
        assert output.get("is_complete") is False

    def test_evaluate_answer_and_advance_to_next_topic(self):
        # Comprehensive answer advances to next topic without follow-up
        state: InterviewState = {
            "candidate_message": (
                "Pentru a optimiza o interogare lentă, aș rula mai întâi EXPLAIN ANALYZE pentru a verifica planul de execuție, "
                "aș analiza dacă există Sequential Scans și aș adăuga un index compus dacă filtrăm pe mai multe coloane. "
                "De asemenea, aș verifica dacă statisticele din PostgreSQL sunt actualizate cu ANALYZE și aș ajusta work_mem dacă este necesar."
            ),
            "active_question_status": "WAITING_ANSWER",
            "active_question_number": 1,
            "active_question_text": "Cum optimizezi o interogare lentă în PostgreSQL?",
            "job_title": "Senior Backend Dev",
            "experience_level": "senior",
            "candidate_name": "Diana Marin",
            "language": "ro",
            "topic_follow_up_count": 0,
            "topics_plan": ["Database Indexing", "Cache Strategy", "System Design"],
            "current_topic_index": 0,
            "assessed_topics": [],
        }

        output = interview_graph.invoke(state)

        assert output.get("intent") == "ANSWER"
        assert output.get("needs_follow_up") is False
        assert "Database Indexing" in output.get("assessed_topics", [])
        assert output.get("current_topic_index") == 1
        assert output.get("active_question_number") == 2
        assert output.get("is_complete") is False

    def test_interview_completion_detection(self):
        # When all topics are exhausted or time expired, workflow enters final evaluation
        state: InterviewState = {
            "candidate_message": "Pentru cache aș alege Redis cu politică de evaporare LRU și TTL clar pentru a preveni stale data.",
            "active_question_status": "WAITING_ANSWER",
            "active_question_number": 3,
            "active_question_text": "Cum implementezi caching-ul în producție?",
            "job_title": "Backend Dev",
            "experience_level": "mid",
            "candidate_name": "Marian Dobre",
            "language": "ro",
            "topics_plan": ["API Design", "Database", "Caching"],
            "current_topic_index": 2,  # Last topic!
            "assessed_topics": ["API Design", "Database"],
        }

        output = interview_graph.invoke(state)

        assert output.get("intent") == "ANSWER"
        assert output.get("is_complete") is True
        assert output.get("active_question_status") == "COMPLETED"
        assert "[INTERVIEW_COMPLETE]" in output.get("turn_prompt", "")

    def test_language_switch_workflow(self):
        state: InterviewState = {
            "candidate_message": "Can we switch to English please?",
            "active_question_status": "WAITING_ANSWER",
            "active_question_number": 2,
            "active_question_text": "Cum gestionezi starea într-o aplicație React?",
            "job_title": "Frontend Engineer",
            "experience_level": "mid",
            "candidate_name": "Bogdan Rusu",
            "language": "ro",
            "topics_plan": ["React State", "CSS Architecture"],
            "current_topic_index": 0,
        }

        output = interview_graph.invoke(state)

        assert output.get("intent") == "LANGUAGE_SWITCH:en"
        assert output.get("language") == "en"
        assert "ENGLISH" in output.get("turn_prompt", "")
        assert output.get("is_complete") is False

    def test_guardrail_inappropriate_language(self):
        state: InterviewState = {
            "candidate_message": "Ce întrebare de rahat, ești un idiot!",
            "active_question_status": "WAITING_ANSWER",
            "active_question_number": 1,
            "active_question_text": "Ce este un closure în JavaScript?",
            "job_title": "Frontend Dev",
            "experience_level": "junior",
            "candidate_name": "Test User",
            "language": "ro",
            "topics_plan": ["JS Basics"],
            "current_topic_index": 0,
        }

        output = interview_graph.invoke(state)

        assert output.get("intent") == "PROFANE_LANGUAGE"
        assert "limbaj nepotrivit" in output.get("turn_prompt", "")
        assert output.get("is_complete") is False
