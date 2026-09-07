from langgraph.graph import StateGraph, START, END
from llm.agent.state import InterviewState
from llm.agent.nodes import (
    start_interview_node,
    process_candidate_response_node,
    detect_clarification_node,
    detect_refusal_node,
    evaluate_answer_node,
    generate_follow_up_node,
    move_to_next_question_node,
    language_switch_node,
    generate_final_evaluation_node,
    guardrail_node,
)

def route_candidate_intent(state: InterviewState) -> str:
    """
    Router conditional edge: Directs candidate input based on classified intent.
    """
    intent = state.get("intent", "ANSWER")
    if intent.startswith("LANGUAGE_SWITCH"):
        return "language_switch"
    if intent == "CLARIFICATION":
        return "detect_clarification"
    if intent == "REFUSAL":
        return "detect_refusal"
    if intent in ("PROFANE_LANGUAGE", "OFF_TOPIC"):
        return "guardrail"
    if intent == "WRAP_UP":
        return "generate_final_evaluation"
    if intent == "GREETING":
        return "start_interview"
    return "evaluate_answer"

def route_after_refusal(state: InterviewState) -> str:
    """
    Refusal conditional edge: Conclude interview if all topics exhausted, otherwise end turn and wait for answer.
    """
    if state.get("is_complete", False):
        return "generate_final_evaluation"
    return END

def route_after_evaluation(state: InterviewState) -> str:
    """
    Evaluation conditional edge: Decides whether to conclude, probe with a follow-up, or advance to next topic.
    """
    if state.get("is_complete", False):
        return "generate_final_evaluation"
    if state.get("needs_follow_up", False):
        return "generate_follow_up"
    return "move_to_next_question"

def build_interview_graph():
    """
    Constructs and compiles the full LangGraph StateGraph governing the conversational interview workflow:
    1. start_interview
    2. process_candidate_response (router)
    3. detect_clarification
    4. detect_refusal_skip
    5. evaluate_answer
    6. generate_follow_up (when response is brief/shallow)
    7. move_to_next_question
    8. detect_interview_completion
    9. generate_final_evaluation
    """
    workflow = StateGraph(InterviewState)

    # 1. Register Nodes
    workflow.add_node("start_interview", start_interview_node)
    workflow.add_node("process_candidate_response", process_candidate_response_node)
    workflow.add_node("language_switch", language_switch_node)
    workflow.add_node("detect_clarification", detect_clarification_node)
    workflow.add_node("detect_refusal", detect_refusal_node)
    workflow.add_node("evaluate_answer", evaluate_answer_node)
    workflow.add_node("generate_follow_up", generate_follow_up_node)
    workflow.add_node("move_to_next_question", move_to_next_question_node)
    workflow.add_node("generate_final_evaluation", generate_final_evaluation_node)
    workflow.add_node("guardrail", guardrail_node)

    # 2. Graph Entry: Start with candidate response processing
    workflow.add_edge(START, "process_candidate_response")

    # 3. Intent Routing
    workflow.add_conditional_edges(
        "process_candidate_response",
        route_candidate_intent,
        {
            "language_switch": "language_switch",
            "detect_clarification": "detect_clarification",
            "detect_refusal": "detect_refusal",
            "guardrail": "guardrail",
            "evaluate_answer": "evaluate_answer",
            "generate_final_evaluation": "generate_final_evaluation",
            "start_interview": "start_interview",
        },
    )

    # 4. Clarification, Language Switch, Guardrail end turn waiting for candidate reply
    workflow.add_edge("language_switch", END)
    workflow.add_edge("detect_clarification", END)
    workflow.add_edge("guardrail", END)
    workflow.add_edge("start_interview", END)

    # 5. Refusal conditional routing
    workflow.add_conditional_edges(
        "detect_refusal",
        route_after_refusal,
        {
            "generate_final_evaluation": "generate_final_evaluation",
            END: END,
        },
    )

    # 6. Evaluation routing (follow-up vs next question vs wrap-up)
    workflow.add_conditional_edges(
        "evaluate_answer",
        route_after_evaluation,
        {
            "generate_final_evaluation": "generate_final_evaluation",
            "generate_follow_up": "generate_follow_up",
            "move_to_next_question": "move_to_next_question",
        },
    )

    # 7. Final turn completion edges
    workflow.add_edge("generate_follow_up", END)
    workflow.add_edge("move_to_next_question", END)
    workflow.add_edge("generate_final_evaluation", END)

    return workflow.compile()

# Singleton compiled LangGraph agent instance
interview_graph = build_interview_graph()
