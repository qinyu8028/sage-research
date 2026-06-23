import json
import logging
import re
import uuid

from sage_research.tools.base_tool import BaseTool, ToolCallError
from ..base import AgentBase, llm_client, Message
from ..context import ContextBuilder
from .prompts import (
    RESEARCHER_SYSTEM_PROMPT,
    RESEARCHER_USER_PROMPT,
    RESEARCHER_COMPRESS_SYSTEM,
    RESEARCHER_COMPRESS_USER,
    RESEARCHER_RETRY_USER_PROMPT,
    RESEARCHER_MAX_STEPS_PROMPT,
    RESEARCHER_DENOISE_SYSTEM,
    RESEARCHER_DENOISE_USER,
)


logger = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 20000
MAX_DENOISE_RESULT_CHARS = 10000


class Researcher(AgentBase):
    """ReAct 循环研究员，接收子问题后通过工具搜索、观察、推理，输出经压缩的研究笔记。"""

    def __init__(
        self,
        name: str,
        llm: llm_client,
        context_builder: ContextBuilder,
        tool_list: list[BaseTool],
        max_steps: int = 3,
        system_prompt: str = RESEARCHER_SYSTEM_PROMPT,
    ):
        super().__init__(name, llm, context_builder, system_prompt)
        self.max_steps = max_steps
        self.tool_schema = [tool.to_schema() for tool in tool_list]
        self._tool_map = {tool.name: tool for tool in tool_list}

    def run(self, sub_question: str, note_feedback: str | None = None) -> str:
        logger.info("[Researcher:%s] run: retry=%s", self.name, bool(note_feedback))

        if not note_feedback:
            prompt = RESEARCHER_USER_PROMPT.format(sub_question=sub_question)
        else:
            prompt = RESEARCHER_RETRY_USER_PROMPT.format(sub_question=sub_question, note_feedback=note_feedback)

        user_msg = Message(role="user", content=prompt)
        self._history.append(user_msg)

        exhausted = True
        tool_call_counts = {}
        for i in range(self.max_steps):
            self.context_builder.compress_old_rounds(self._history, sub_question, self.system_prompt)
            logger.info("[Researcher:%s] step %d/%d, history: %d 条消息", self.name, i + 1, self.max_steps, len(self._history))
            
            messages = self._build_messages(self.system_prompt)
            response = self.llm.invoke(
                messages=messages,
                tools=self.tool_schema,
                tag=f"{self.name}:react",
            )

            if response.tool_calls:
                tool_call_msg = Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=[tool_call.model_dump() for tool_call in response.tool_calls]
                )
                self._history.append(tool_call_msg)

                for tool_call in response.tool_calls:
                    name = tool_call.function.name
                    parameters = json.loads(tool_call.function.arguments)
                    tool_call_counts[name] = tool_call_counts.get(name, 0) + 1
                    self._execute_tool(name, parameters, tool_call.id, sub_question)

            # parse text
            elif parsed := self._parse_text_tool_call(response.content):
                logger.info("[Researcher:%s] fallback: 从文本解析到 %d 个工具调用", self.name, len(parsed))
                fake_tool_calls = []
                for name, parameters in parsed:
                    call_id = f"fallback_{uuid.uuid4().hex[:8]}"
                    fake_tool_calls.append({
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(parameters, ensure_ascii=False),
                        },
                    })

                self._history.append(Message(
                    role="assistant", content="", tool_calls=fake_tool_calls,
                ))

                for idx, (name, parameters) in enumerate(parsed):
                    tool_call_counts[name] = tool_call_counts.get(name, 0) + 1
                    self._execute_tool(name, parameters, fake_tool_calls[idx]["id"], sub_question)

            else:
                logger.info("[Researcher:%s] 推理完成, step %d (%d 字符)", self.name, i + 1, len(response.content))
                response_msg = Message(role="assistant", content=response.content)
                self._history.append(response_msg)
                exhausted = False
                break
        
        if exhausted:
            logger.info("[Researcher:%s] max_steps 耗尽, 强制总结", self.name)
            prompt = RESEARCHER_MAX_STEPS_PROMPT
            max_iter_msg = Message(content=prompt, role="user")
            self._history.append(max_iter_msg)

            messages = self._build_messages(self.system_prompt)
            response = self.llm.invoke(
                messages=messages,
                tag=f"{self.name}:forced_summary",
            )
            response_msg = Message(role="assistant", content=response.content)
            self._history.append(response_msg)
            result = response.content
        else:
            result = self._compress(response.content)

        steps_taken = self.max_steps if exhausted else i + 1
        logger.info(
            "[Researcher:%s] 完成: %d/%d 步, 工具调用: %s, history: %d 条消息, output: %d 字符%s",
            self.name, steps_taken, self.max_steps,
            dict(tool_call_counts), len(self._history),
            len(result), "" if exhausted else f" (compress: {len(response.content)} -> {len(result)})",
        )

        return result, dict(tool_call_counts)

    def _compress(self, raw_research: str) -> str:
        messages = [
            {"role": "system", "content": RESEARCHER_COMPRESS_SYSTEM},
            {"role": "user", "content": RESEARCHER_COMPRESS_USER.format(raw_research=raw_research)}
        ]
        compress_response = self.llm.invoke(
            messages=messages,
            tag=f"{self.name}:compress",
        )
        
        return compress_response.content

    def _execute_tool(self, name: str, parameters: dict, tool_call_id: str, sub_question: str):
        logger.info("[Researcher:%s] 调用工具: %s, 参数: %.200s", self.name, name, json.dumps(parameters, ensure_ascii=False))

        tool = self._tool_map.get(name)
        if tool is None:
            tool_result = f"Error: tool '{name}' does not exist. Available tools: {list(self._tool_map.keys())}"
            logger.warning("[Researcher:%s] 工具不存在: %s", self.name, name)

        else:
            try:
                tool_result = tool.run_tool(parameters)
                raw_len = len(tool_result)

                if raw_len > MAX_TOOL_RESULT_CHARS:
                    tool_result = tool_result[:MAX_TOOL_RESULT_CHARS]
                    tool_result += f"\n\n[截断: 原始 {raw_len} 字符, 保留 {MAX_TOOL_RESULT_CHARS} 字符]"
                    logger.info("[Researcher:%s] 工具结果截断: %s %d -> %d 字符", self.name, name, raw_len, MAX_TOOL_RESULT_CHARS)

                if name in {"mcp__fetch__fetch"}:
                    pre_denoise_len = len(tool_result)
                    tool_result = self._denoise(sub_question=sub_question, raw_tool_result=tool_result)
                    logger.info("[Researcher:%s] denoise: %s, %d -> %d 字符 (%.0f%%保留)", self.name, name, pre_denoise_len, len(tool_result), len(tool_result) / pre_denoise_len * 100)
                    if len(tool_result) > MAX_DENOISE_RESULT_CHARS:
                        original_len = len(tool_result)
                        tool_result = tool_result[:MAX_DENOISE_RESULT_CHARS]
                        logger.info("[Researcher:%s] denoise 结果截断: %d -> %d 字符", self.name, original_len, MAX_DENOISE_RESULT_CHARS)
                else:
                    logger.info("[Researcher:%s] 工具结果: %s, %d 字符", self.name, name, raw_len)

            except ToolCallError as e:
                tool_result = str(e)
                logger.error("[Researcher:%s] 工具失败: %s - %s", self.name, name, tool_result)

        self._history.append(Message(
            role="tool", content=tool_result, tool_call_id=tool_call_id,
        ))

    def _parse_text_tool_call(self, content: str) -> list[tuple[str, dict]] | None:
        tool_names = "|".join(re.escape(name) for name in self._tool_map)
        pattern = rf"\b({tool_names})\((.+)\)"

        results = []
        for match in re.finditer(pattern, content):
            name = match.group(1)
            args_str = match.group(2).strip()

            try:
                params = json.loads(args_str)
                if isinstance(params, dict):
                    results.append((name, params))
                    continue
            except (json.JSONDecodeError, TypeError):
                pass

            str_match = re.match(r'^["\'](.+)["\']$', args_str)
            if str_match:
                first_param = self._get_first_param(name)
                results.append((name, {first_param: str_match.group(1)}))

        return results if results else None

    def _get_first_param(self, tool_name: str) -> str:
        for schema in self.tool_schema:
            if schema["function"]["name"] == tool_name:
                params = schema["function"]["parameters"]
                if params.get("required"):
                    return params["required"][0]
                if params.get("properties"):
                    return next(iter(params["properties"]))
        return "query"

    def _denoise(self, sub_question: str, raw_tool_result: str) -> str:
        if len(raw_tool_result) < 2000:
            return raw_tool_result

        messages = [
            {"role": "system", "content": RESEARCHER_DENOISE_SYSTEM},
            {"role": "user", "content": RESEARCHER_DENOISE_USER.format(
                sub_question=sub_question, tool_result=raw_tool_result
            )}
        ]
        denoise_response = self.llm.invoke(
            messages=messages,
            tag=f"{self.name}:denoise",
        )
        return denoise_response.content