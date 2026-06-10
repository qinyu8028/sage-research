import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..base import AgentBase, llm_client, Message, Config
from ..context import ContextBuilder
from .prompts import (
    SUPERVISOR_PLAN_SYSTEM,
    SUPERVISOR_PLAN_USER,
    SUPERVISOR_REPLAN_USER,
    SUPERVISOR_REVIEW_SYSTEM,
    SUPERVISOR_REVIEW_USER,
    SUPERVISOR_COVERED_SECTION,
)


class SubQuestion(BaseModel):
    question: str = Field(
        description="A detailed, self-contained research sub-question with full context. "
        "Must be specific enough for an independent Researcher to work on without any other information. "
        "At least one full paragraph."
    )
    rationale: str = Field(
        description="Why this sub-question deserves separate investigation and what unique dimension it covers."
    )


class NoteReview(BaseModel):
    verdict: Literal["approved", "retry", "revise"] = Field(
        description="approved: research is sufficient. "
        "retry: right topic but needs more depth or sources, send back to Researcher. "
        "revise: the sub-question itself is flawed, needs supplementary planning."
    )
    feedback: str = Field(
        default="",
        description="For retry: list exactly what is missing or needs sources. "
        "For revise: explain what is wrong with the sub-question. "
        "Empty for approved.",
    )


class ReviewResult(BaseModel):
    note_reviews: list[NoteReview]
    missing_dimensions: str = ""


class Supervisor(AgentBase):
    """
    研究流水线的管理者，负责规划和审查两个阶段。
    plan() 将研究简报拆分为子问题分配给 Researcher，review() 审查研究结果并决定通过、重试或补充规划。
    """

    def __init__(
        self,
        llm: llm_client,
        context_builder: ContextBuilder,
        name: str = "supervisor",
        system_prompt: str = SUPERVISOR_PLAN_SYSTEM,
        config: Config | None = None,
    ):
        super().__init__(name, llm, context_builder, system_prompt, config)

        subquestion_schema = SubQuestion.model_json_schema()
        self.output_schema = {
            "type": "function",
            "function": {
                "name": "create_research_plan",
                "description": "Decompose the research brief into 3-5 focused, independent sub-questions for parallel research.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sub_questions": {"type": "array", "items": subquestion_schema}
                    },
                    "required": ["sub_questions"],
                },
            },
        }

        note_review_schema = NoteReview.model_json_schema()
        self.review_schema = {
            "type": "function",
            "function": {
                "name": "submit_review",
                "description": "Submit review results for all research note pairs. One review per pair, in input order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note_reviews": {"type": "array", "items": note_review_schema},
                        "missing_dimensions": {
                            "type": "string",
                            "description": "Dimensions of the research brief not covered by any existing sub-question. Empty string if coverage is adequate.",
                        },
                    },
                    "required": ["note_reviews"],
                },
            },
        }

    def plan(
        self,
        research_brief: str,
        passed: list[str] | None = None,
        feedback: list[str] | None = None,
    ) -> list[SubQuestion]:
        """
        将研究简报拆分为可独立执行的子问题，通过 function calling 输出结构化结果。
        当 passed 和 feedback 有值时进入补充规划模式，仅生成填补缺口的子问题。
        """

        if feedback is None:
            # plan stage
            prompt = SUPERVISOR_PLAN_USER.format(research_brief=research_brief)
        else:
            # replan stage
            prompt = SUPERVISOR_REPLAN_USER.format(
                research_brief=research_brief, covered=passed, feedback=feedback
            )

        brief_msg = Message(content=prompt, role="user")
        self._history.append(brief_msg)
        messages = self._build_messages(self.system_prompt)

        plan_response = self.llm.invoke(
            messages=messages,
            tool_choice="required",
            tools=[self.output_schema],
        )

        response_msg = Message(
            content=plan_response.content,
            role="assistant",
            tool_calls=[
                tool_call.model_dump() for tool_call in plan_response.tool_calls
            ],
        )
        self._history.append(response_msg)

        # process the output
        json_response = plan_response.tool_calls[0].function.arguments
        result = json.loads(json_response)

        subquestion_list = [
            SubQuestion(**raw_result) for raw_result in result["sub_questions"]
        ]

        return subquestion_list

    def review(
        self,
        research_brief: str,
        to_be_reviewed: list[tuple[str, str]],
        passed: list[str] | None = None,
    ) -> ReviewResult:
        """
        逐条审查 (子问题, 研究笔记) 配对，通过 function calling 输出结构化审查结果。
        每条配对获得 approved/retry/revise 判定，同时评估整体是否有遗漏维度。
        """

        if passed:
            items = "\n".join(f"- {q}" for q in passed)
            covered_section = SUPERVISOR_COVERED_SECTION.format(passed=items)
        else:
            covered_section = ""

        if to_be_reviewed:
            items = "\n".join(
                f"<pair>\n<sub_question>\n{sub_q}\n</sub_question>\n<research_note>\n{note}\n</research_note>\n</pair>"
                for sub_q, note in to_be_reviewed
            )
            pairs = f"<pairs_to_review>\n{items}\n</pairs_to_review>"
        else:
            pairs = ""

        prompt = SUPERVISOR_REVIEW_USER.format(
            research_brief=research_brief,
            covered_section=covered_section,
            pairs=pairs,
        )

        review_msg = Message(content=prompt, role="user")
        self._history.append(review_msg)
        messages = self._build_messages(SUPERVISOR_REVIEW_SYSTEM)

        review_response = self.llm.invoke(
            messages=messages,
            tool_choice="required",
            tools=[self.review_schema],
        )

        response_msg = Message(
            content=review_response.content,
            role="assistant",
            tool_calls=[
                tool_call.model_dump() for tool_call in review_response.tool_calls
            ],
        )
        self._history.append(response_msg)

        # process the output
        json_response = review_response.tool_calls[0].function.arguments
        result: dict[str, Any] = json.loads(json_response)

        review_result = ReviewResult(**result)

        return review_result
