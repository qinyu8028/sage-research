import json
import logging
from typing import Literal

from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel, Field

from ..base import AgentBase, llm_client, Message
from ..context import ContextBuilder
from .prompts import (
    SUPERVISOR_SYSTEM,
    SUPERVISOR_PLAN_USER,
    SUPERVISOR_REPLAN_USER,
    SUPERVISOR_REVIEW_USER,
    SUPERVISOR_COVERED_SECTION,
)

logger = logging.getLogger(__name__)


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
    note_feedback: str = Field(
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
        max_steps: int,
        name: str = "supervisor",
        system_prompt: str = SUPERVISOR_SYSTEM,
    ):
        super().__init__(name, llm, context_builder, system_prompt)
        self.max_steps = max_steps

        subquestion_schema = SubQuestion.model_json_schema()
        self.output_schema = {
            "type": "function",
            "function": {
                "name": "create_research_plan",
                "description": "Decompose the research brief into 3-4 focused, independent sub-questions for parallel research.",
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

    def run(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError("Supervisor uses plan() and review(), not run()")

    def _parse_tool_response(
        self, response: ChatCompletionMessage, expected_func: str, wrap_key: str | None = None
    ) -> dict:
        """
        从 LLM 响应中提取结构化结果。
        优先从 tool_calls 解析；若模型未返回 tool_call（弱模型常见），
        则从 content 中解析 JSON，依次处理 markdown 代码块、函数名前缀、裸数组包装。
        """
        if response.tool_calls:
            return json.loads(response.tool_calls[0].function.arguments)

        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if content.startswith(expected_func):
            content = content[len(expected_func) :].strip()
        if wrap_key and content.startswith("["):
            return {wrap_key: json.loads(content)}
        return json.loads(content)

    def _record_response(self, response: ChatCompletionMessage, result: dict):
        """
        将 LLM 响应追加到 _history。
        tool_call 模式记录 assistant(tool_calls) + tool(result) 两条消息；
        fallback 模式作为普通 assistant 消息记录。
        """
        if response.tool_calls:
            tc = response.tool_calls[0]
            self._history.append(Message(
                content=response.content,
                role="assistant",
                tool_calls=[tc.model_dump() for tc in response.tool_calls],
            ))
            self._history.append(Message(
                content=json.dumps(result, ensure_ascii=False),
                role="tool",
                tool_call_id=tc.id,
            ))
        else:
            self._history.append(Message(
                content=response.content,
                role="assistant",
            ))

    def plan(
        self,
        research_brief: str,
        approved_pairs: list[tuple[str, str]] | None = None,
        review_result: ReviewResult | None = None,
    ) -> list[SubQuestion]:
        """
        将研究简报拆分为可独立执行的子问题，通过 function calling 输出结构化结果。
        当 review_result 有值时进入补充规划模式，仅生成填补缺口的子问题。
        """

        if review_result is None:
            prompt = SUPERVISOR_PLAN_USER.format(research_brief=research_brief, max_steps=self.max_steps)
        else:
            approved_str = "\n".join(
                f"- {q}" for q, _ in approved_pairs
            ) if approved_pairs else ""

            revision_points = [
                nr.note_feedback for nr in review_result.note_reviews
                if nr.verdict == "revise" and nr.note_feedback
            ]
            if review_result.missing_dimensions:
                revision_points.append(review_result.missing_dimensions)
            revision_str = "\n".join(f"- {rp}" for rp in revision_points)

            prompt = SUPERVISOR_REPLAN_USER.format(
                research_brief=research_brief,
                approved_questions=approved_str,
                revision_points=revision_str,
                max_steps=self.max_steps,
            )

        brief_msg = Message(content=prompt, role="user")
        self._history.append(brief_msg)
        messages = self._build_messages()

        response = self.llm.invoke(
            messages=messages,
            tool_choice="required",
            tools=[self.output_schema],
            tag="supervisor:plan",
        )

        result = self._parse_tool_response(
            response, "create_research_plan", wrap_key="sub_questions"
        )
        self._record_response(response, result)

        sub_questions = [SubQuestion(**item) for item in result["sub_questions"]]
        logger.info("[Supervisor] plan: 生成 %d 个子问题", len(sub_questions))
        return sub_questions

    def review(
        self,
        research_brief: str,
        pending_review_pairs: list[tuple[str, str]],
        approved_pairs: list[tuple[str, str]] | None = None,
    ) -> ReviewResult:
        """
        逐条审查 (子问题, 研究笔记) 配对，通过 function calling 输出结构化审查结果。
        每条配对获得 approved/retry/revise 判定，同时评估整体是否有遗漏维度。
        """

        if approved_pairs:
            items = "\n".join(f"- {q}" for q, _ in approved_pairs)
            covered_section = SUPERVISOR_COVERED_SECTION.format(approved_questions=items)
        else:
            covered_section = ""

        if pending_review_pairs:
            items = "\n".join(
                f"<pair>\n<sub_question>\n{sub_q}\n</sub_question>\n<research_note>\n{note}\n</research_note>\n</pair>"
                for sub_q, note in pending_review_pairs
            )
            pairs = f"<pairs_to_review>\n{items}\n</pairs_to_review>"
        else:
            pairs = ""

        prompt = SUPERVISOR_REVIEW_USER.format(
            research_brief=research_brief,
            covered_section=covered_section,
            pairs=pairs,
            pair_count=len(pending_review_pairs),
        )

        review_msg = Message(content=prompt, role="user")
        self._history.append(review_msg)
        messages = self._build_messages()

        response = self.llm.invoke(
            messages=messages,
            tool_choice="required",
            tools=[self.review_schema],
            tag="supervisor:review",
        )

        result = self._parse_tool_response(response, "submit_review", wrap_key="note_reviews")
        self._record_response(response, result)

        review_result = ReviewResult(**result)
        for i, nr in enumerate(review_result.note_reviews):
            if nr.verdict != "approved":
                logger.info("[Supervisor] review[%d]: %s — %s", i, nr.verdict, nr.note_feedback)
            else:
                logger.info("[Supervisor] review[%d]: approved", i)
        if review_result.missing_dimensions:
            logger.info("[Supervisor] missing_dimensions: %s", review_result.missing_dimensions)
        return review_result
