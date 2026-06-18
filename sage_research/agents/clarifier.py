import json
import logging

from ..base.llm_client import TestAgent as llm_client
from .prompts import CLARIFIER_SYSTEM, CLARIFIER_USER, CLARIFIER_REFINE_USER

logger = logging.getLogger(__name__)


analyze_schema = {
    "type": "function",
    "function": {
        "name": "analyze_query",
        "description": "Analyze whether the user query is specific enough for research, or needs clarification.",
        "parameters": {
            "type": "object",
            "properties": {
                "is_clear": {
                    "type": "boolean",
                    "description": "True if the query is specific enough to start research directly.",
                },
                "research_brief": {
                    "type": "string",
                    "description": "A refined, detailed research brief. Populated when is_clear is true.",
                },
                "clarifying_questions": {
                    "type": "string",
                    "description": "Numbered list of 2-4 questions to ask the user. Populated when is_clear is false.",
                },
            },
            "required": ["is_clear"],
        },
    },
}


class Clarifier:
    def __init__(self, llm: llm_client, system_prompt: str = CLARIFIER_SYSTEM):
        self.llm = llm
        self.system_prompt = system_prompt

    def run(self, raw_query: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": CLARIFIER_USER.format(raw_query=raw_query)},
        ]
        response = self.llm.invoke(
            messages=messages,
            tools=[analyze_schema],
            tool_choice={"type": "function", "function": {"name": "analyze_query"}},
            tag="clarifier:analyze",
        )

        if not response.tool_calls:
            logger.warning("[Clarifier] function calling 失败，直接使用原始 query")
            return raw_query

        args: dict = json.loads(response.tool_calls[0].function.arguments)

        if args.get("is_clear"):
            brief = args.get("research_brief", raw_query)
            logger.info("[Clarifier] query 足够具体，生成 research_brief")
            return brief

        questions = args.get("clarifying_questions", "")
        print(f"\n需要澄清研究范围:\n{questions}")

        user_response = input("\n请回答以上问题: ").strip()
        if not user_response:
            logger.info("[Clarifier] 用户未回答，直接使用原始 query")
            return raw_query

        refine_messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": CLARIFIER_REFINE_USER.format(
                raw_query=raw_query, user_response=user_response
            )},
        ]
        refine_response = self.llm.invoke(messages=refine_messages, tag="clarifier:refine")
        logger.info("[Clarifier] 生成 research_brief 完成")
        return refine_response.content
