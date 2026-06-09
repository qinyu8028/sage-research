from typing import Any

from ..memory.manager import MemoryManager
from .base_tool import BaseTool, ToolParameter


class WorkingMemoryTool(BaseTool):
    def __init__(self, memory_manager: MemoryManager):
        super().__init__(
            name="working_memory",
            description=(
                "保存当前对话中临时性的、可能会变化的信息。"
                "适用于：当前讨论的话题背景、用户提出但尚未确认的想法、对话中的中间结论。"
                "不适用于保存用户身份、确定的偏好或明确的决策(应使用semantic_memory)，也不要保存闲聊内容。"
                "返回保存确认信息。临时记忆会随时间衰减，重要内容会在对话结束时自动整合到长期记忆。"
            ),
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="用第三人称陈述句改写，不要复制用户原话。例：用户说'我喜欢用Python'→存'用户偏好使用Python进行编程'"
                ),
                ToolParameter(
                    name="importance",
                    type="number",
                    description="重要性评分(0-1)。参考：用户提到的临时需求→0.4，正在讨论的技术问题→0.5，对话中产生的中间结论→0.6"
                )
            ]
        )
        self.memory_manager = memory_manager

    def run_tool(self, parameters: dict[str, Any]) -> str:
        self.memory_manager.add_to_working(
            content=parameters["content"], importance=parameters["importance"]
        )
        return "Working memory saved."


class SemanticMemoryTool(BaseTool):
    def __init__(self, memory_manager: MemoryManager):
        super().__init__(
            name="semantic_memory",
            description=(
                "保存需要跨对话长期记住的确定性信息。"
                "适用于：用户身份(如名字、职业)、明确的偏好、已确认的决策、重要的事实结论。"
                "不适用于保存临时性信息、未确认的想法或闲聊内容(应使用working_memory)。保存前应检查索引中是否已有类似记忆，有则用相同name更新而非重复创建。"
                "返回保存确认信息。长期记忆持久存储，不会自动衰减。"
            ),
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="用第三人称结构化改写，包含关键信息。例：用户说'我叫小明，大三，正在用Python学Agent'→存'用户小明，大三学生，正在学习AI Agent开发，偏好Python'"
                ),
                ToolParameter(
                    name="importance",
                    type="number",
                    description="重要性评分(0-1)。参考：重要技术结论→0.7，明确的偏好或决策→0.8，用户身份信息(名字、职业)→0.9"
                ),
                ToolParameter(
                    name="name",
                    type="string",
                    description="记忆的唯一标识，使用英文kebab-case命名，2-4个词。例：user-identity、prefer-python、use-langchain"
                ),
                ToolParameter(
                    name="description",
                    type="string",
                    description="一句话中文描述，概括记忆的核心内容，用于索引检索"
                )
            ]
        )
        self.memory_manager = memory_manager

    def run_tool(self, parameters: dict[str, Any]) -> str:
        self.memory_manager.add_to_semantic(
            content=parameters["content"], 
            importance=parameters["importance"], 
            name=parameters["name"], 
            description=parameters["description"]
        )
        return "Semantic memory saved."
