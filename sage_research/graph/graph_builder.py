import operator

from typing import Annotated, Callable, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from sage_research.agents.supervisor import ReviewResult, SubQuestion
from ..agents import Supervisor, Writer, Researcher


def pending_review_reducer(existing: list, new: list) -> list:
    if not new:
        return []
    else:
        return existing + new


class State(TypedDict):
    research_brief: str
    sub_questions: list[SubQuestion]
    review_result: ReviewResult
    approved_pairs: Annotated[list[tuple[str, str]], operator.add]
    pending_review_pairs: Annotated[list[tuple[str, str]], pending_review_reducer]
    refine_round: int
    final_report: str
    retry_items: list[dict]

# TODO: add clarify node
# class InputSchema(TypedDict):
#     raw_query: str


class InputSchema(TypedDict):
    research_brief: str


class OutputSchema(TypedDict):
    final_report: str

    
def build_graph(
    supervisor: Supervisor, 
    create_researcher: Callable[[], Researcher],
    writer: Writer, 
    max_rounds: int = 3
):
    builder = StateGraph(
        State, input_schema=InputSchema, output_schema=OutputSchema
    )

    def hand_out_subquestion(state: State) -> Send:
        return [
            Send(
                "research_node", 
                {
                    "sub_question": sq.question, 
                    "note_feedback": ""
                }
            )
            for sq in state["sub_questions"]
        ]

    def reviewer_route(state: State) -> str:
        if state["refine_round"] > max_rounds:
            return "write_node"

        verdicts = {note_review.verdict for note_review in state["review_result"].note_reviews}

        if verdicts == {"approved"} and not state["review_result"].missing_dimensions:
            return "write_node"

        if verdicts <= {"approved", "retry"} and not state["review_result"].missing_dimensions:
            return [Send("research_node", item) for item in state["retry_items"]]

        return "plan_node"

    # TODO: add clarify node
    # def clarify_node(state: ResearchState):

    def plan_node(state: State) -> dict[str, SubQuestion]:
        result = supervisor.plan(
            research_brief=state["research_brief"],
            approved_pairs=state.get("approved_pairs"),
            review_result=state.get("review_result"),
        )
        return {"sub_questions": result}

    def research_node(state: dict) -> dict:
        researcher = create_researcher()
        result = researcher.run(
            sub_question=state["sub_question"], note_feedback=state["note_feedback"]
        )
        return {"pending_review_pairs": [(state["sub_question"], result)]}

    def review_node(state: State) -> dict:
        result = supervisor.review(
            research_brief=state["research_brief"],
            pending_review_pairs=state["pending_review_pairs"],
            approved_pairs=state.get("approved_pairs", [])
        )
        approved_pairs = [
            state["pending_review_pairs"][i]
            for i, note_review in enumerate(result.note_reviews)
            if note_review.verdict == "approved"
        ]
        retry_items = [
            {
                "sub_question": state["pending_review_pairs"][i][0],
                "note_feedback": note_review.note_feedback
            }
            for i, note_review in enumerate(result.note_reviews)
            if note_review.verdict == "retry"
        ]

        return {
            "review_result": result,
            "approved_pairs": approved_pairs,
            "refine_round": state.get("refine_round", 0) + 1,
            "pending_review_pairs": [],
            "retry_items": retry_items,
        }

    def write_node(state: State) -> dict:
        result = writer.run(
            research_brief=state["research_brief"],
            clean_notes=[note for _, note in state["approved_pairs"]],
        )
        return {"final_report": result}

    # add node
    # builder.add_node("clarify_node", clarify_node)
    builder.add_node("plan_node", plan_node)
    builder.add_node("research_node", research_node)
    builder.add_node("review_node", review_node)
    builder.add_node("write_node", write_node)

    # add edge
    # builder.add_edge(START, "clarify_node")
    # builder.add_edge("clarify_node", "plan_node")
    builder.add_edge(START, "plan_node")
    builder.add_conditional_edges("plan_node", hand_out_subquestion, ["research_node"])
    builder.add_edge("research_node", "review_node")
    builder.add_conditional_edges("review_node", reviewer_route, ["plan_node", "research_node", "write_node"])
    builder.add_edge("write_node", END)

    return builder.compile()