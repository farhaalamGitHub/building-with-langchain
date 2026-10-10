r"""Stories 4.1 and 4.2: the routing and bounded-review workflow as a small LangGraph graph.

START -> router --(general)--> general_chat --\
                \-(study)----> study_helper ---+--> reviewer --(approve)--> END
                \-(empty /study)--> END                 \--(improve, only when revision_count
                                                         is 0)--> improver --> reviewer
"""

import operator
import re
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph

from learning_companion.chain import (
    build_chain,
    build_improver_chain,
    build_reviewer_chain,
    build_study_helper_chain,
)
from learning_companion.settings import Settings

EMPTY_STUDY_REPLY = "Add a question after /study, for example: /study What is an API?"

# The improver may rewrite an answer this many times. The reviewer enforces it in plain Python.
MAX_REVISIONS = 1

# "/study" must be followed by whitespace or the end, so "/studying" is an ordinary message.
_STUDY_RULE = re.compile(r"^\s*/study(?:\s+(.*))?$", re.DOTALL)


class GraphState(TypedDict, total=False):
    question: str  # current user message
    history: list[BaseMessage]  # current conversation messages (request-provided, capped)
    route: str  # "general" or "study", written by the router
    draft_answer: str  # current answer text: first draft, then the improver's rewrite
    review_decision: str  # "approve" or "improve", written by the reviewer each time it runs
    review_reason: str  # one short plain-English reason for that decision
    revision_count: int  # how many times the improver has rewritten the draft (0 or 1)
    final_answer: str  # the answer sent to Open WebUI, written when the draft is accepted
    nodes: Annotated[list[str], operator.add]  # trace only: node names in the order they ran


def router(state: GraphState) -> dict:
    """Ordinary Python, not an agent: the visible /study rule."""
    match = _STUDY_RULE.match(state["question"])
    if match is None:
        return {"route": "general", "nodes": ["router"]}
    question = (match.group(1) or "").strip()
    update = {"route": "study", "question": question, "nodes": ["router"]}
    if not question:
        update["final_answer"] = EMPTY_STUDY_REPLY  # no model call, no review; ends right here
    return update


def _after_router(state: GraphState) -> str:
    if state.get("final_answer"):
        return END
    return "general_chat" if state["route"] == "general" else "study_helper"


def _after_reviewer(state: GraphState) -> str:
    return END if state["review_decision"] == "approve" else "improver"


def build_graph(settings: Settings):
    """Raises ConfigurationError when the model settings are missing."""
    general = build_chain(settings)
    study = build_study_helper_chain(settings)
    review = build_reviewer_chain(settings)
    improve = build_improver_chain(settings)

    def general_chat(state: GraphState) -> dict:
        draft = general.invoke({"question": state["question"], "history": state["history"]})
        return {"draft_answer": draft, "nodes": ["general_chat"]}

    def study_helper(state: GraphState) -> dict:
        draft = study.invoke({"question": state["question"], "history": state["history"]})
        return {"draft_answer": draft, "nodes": ["study_helper"]}

    def reviewer(state: GraphState) -> dict:
        draft = state["draft_answer"]
        if state["revision_count"] >= MAX_REVISIONS:
            # The limit is plain Python, not a model decision: accept the current draft.
            return {
                "review_decision": "approve",
                "review_reason": "revision limit reached",
                "final_answer": draft,
                "nodes": ["reviewer"],
            }
        verdict = review.invoke(
            {"route": state["route"], "question": state["question"], "draft": draft}
        )
        update = {
            "review_decision": verdict.decision,
            "review_reason": verdict.reason,
            "nodes": ["reviewer"],
        }
        if verdict.decision == "approve":
            update["final_answer"] = draft
        return update

    def improver(state: GraphState) -> dict:
        better = improve.invoke(
            {
                "route": state["route"],
                "question": state["question"],
                "draft": state["draft_answer"],
                "reason": state["review_reason"],
            }
        )
        return {
            "draft_answer": better,
            "revision_count": state["revision_count"] + 1,
            "nodes": ["improver"],
        }

    graph = StateGraph(GraphState)
    graph.add_node("router", router)
    graph.add_node("general_chat", general_chat)
    graph.add_node("study_helper", study_helper)
    graph.add_node("reviewer", reviewer)
    graph.add_node("improver", improver)
    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", _after_router, ["general_chat", "study_helper", END])
    graph.add_edge("general_chat", "reviewer")
    graph.add_edge("study_helper", "reviewer")
    graph.add_conditional_edges("reviewer", _after_reviewer, ["improver", END])
    graph.add_edge("improver", "reviewer")
    return graph.compile()
