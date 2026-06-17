import json
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


DENOISE_TOOLS = {
    "mcp__fetch__fetch", 
    "mcp__paper-search__read_arxiv_paper",
    "mcp__pdfmux__convert_pdf",
}
MAX_TOOL_RESULT_CHARS = 20000


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
        if not note_feedback:
            prompt = RESEARCHER_USER_PROMPT.format(sub_question=sub_question)
        else:
            prompt = RESEARCHER_RETRY_USER_PROMPT.format(sub_question=sub_question, note_feedback=note_feedback)

        user_msg = Message(role="user", content=prompt)
        self._history.append(user_msg)

        exhausted = True
        for i in range(self.max_steps):
            messages = self._build_messages(self.system_prompt)
            response = self.llm.invoke(
                messages=messages, 
                tools=self.tool_schema
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
                    self._execute_tool(name, parameters, tool_call.id, sub_question)

            elif parsed := self._parse_text_tool_call(response.content):
                print(f"  [Researcher] fallback: 从文本解析到 {len(parsed)} 个工具调用")
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
                    self._execute_tool(name, parameters, fake_tool_calls[idx]["id"], sub_question)

            else:
                print(f"  [Researcher] 推理完成 ({len(response.content)} 字符)")
                response_msg = Message(role="assistant", content=response.content)
                self._history.append(response_msg)
                exhausted = False
                break
        
        if exhausted:
            prompt = RESEARCHER_MAX_STEPS_PROMPT
            max_iter_msg = Message(content=prompt, role="user")
            self._history.append(max_iter_msg)

            messages = self._build_messages(self.system_prompt)
            response = self.llm.invoke(
                messages=messages, 
            )
            response_msg = Message(role="assistant", content=response.content)
            self._history.append(response_msg)
        
        raw_research = response.content
        result = self._compress(raw_research)

        return result

    def _compress(self, raw_research: str) -> str:
        messages = [
            {"role": "system", "content": RESEARCHER_COMPRESS_SYSTEM},
            {"role": "user", "content": RESEARCHER_COMPRESS_USER.format(raw_research=raw_research)}
        ]
        compress_response = self.llm.invoke(
            messages=messages
        )
        
        return compress_response.content

    def _execute_tool(self, name: str, parameters: dict, tool_call_id: str, sub_question: str):
        print(f"  [Researcher] 调用工具: {name}({json.dumps(parameters, ensure_ascii=False)[:200]})")

        tool = self._tool_map.get(name)
        if tool is None:
            tool_result = f"Error: tool '{name}' does not exist. Available tools: {list(self._tool_map.keys())}"
            print(f"  [Researcher] 工具不存在: {name}")
            
        else:
            try:
                tool_result = tool.run_tool(parameters)
                print(f"  [Researcher] 工具结果: {tool_result[:300]}...")
                if len(tool_result) > MAX_TOOL_RESULT_CHARS:
                    original_length = len(tool_result)
                    tool_result = tool_result[:MAX_TOOL_RESULT_CHARS]
                    tool_result += f"\n\n[截断: 原始 {original_length} 字符, 保留 {MAX_TOOL_RESULT_CHARS} 字符]"
                    print(f"  [Researcher] 工具结果过长，截断至 {MAX_TOOL_RESULT_CHARS} 字符...")

                if name in DENOISE_TOOLS:
                    tool_result = self._denoise(sub_question=sub_question, raw_tool_result=tool_result)

            except ToolCallError as e:
                tool_result = str(e)
                print(f"  [Researcher] 工具失败: {tool_result}")

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
        if len(raw_tool_result) < 500:
            return raw_tool_result

        messages = [
            {"role": "system", "content": RESEARCHER_DENOISE_SYSTEM},
            {"role": "user", "content": RESEARCHER_DENOISE_USER.format(
                sub_question=sub_question, tool_result=raw_tool_result
            )}
        ]
        denoise_response = self.llm.invoke(
            messages=messages
        )
        return denoise_response.content