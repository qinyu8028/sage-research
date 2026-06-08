from ..base import TestAgent
from .token_counter import TokenCounter
from ..base import Message


SUMMARY_PROMPT = """<role>
你是一个对话摘要助手，负责将Agent与用户的多轮对话历史压缩为结构化摘要。
</role>

<goal>
生成一段简洁的摘要，使Agent可以仅凭此摘要继续未完成的工作，无需回顾原始对话。
</goal>


<instructions>
从对话历史中提取并保留以下信息：
1. 用户的原始意图和最终目标
2. 已完成的操作及关键结果（包括具体文件名、函数名、错误信息）
3. 调用过的工具名称及其关键返回值
4. 当前任务进度和状态
5. 尚未完成的工作和下一步计划
</instructions>

<output_format>
使用纯文本输出，按以下结构组织：

目标：[一句话描述用户的核心目标]
已完成：[已完成的操作列表]
工具调用记录：[工具名称及关键结果]
当前状态：[进行到哪一步]
待办：[下一步需要做什么]
</output_format>

<examples>
<example>
目标：用户要求在项目中添加文件搜索功能
已完成：1. 创建了 search.py 模块 2. 实现了 glob 匹配逻辑 3. 添加了单元测试（3/5通过）
工具调用记录：read_file(search.py) 获取了现有代码结构；bash(pytest) 发现 test_recursive 和 test_hidden_files 失败
当前状态：搜索功能基本可用，两个边界case的测试未通过
待办：1. 修复递归搜索中的符号链接处理 2. 修复隐藏文件过滤逻辑 3. 全部测试通过后集成到主模块
</example>
</examples>
"""


class HistoryCompactor:
    def __init__(
        self, 
        llm_client: TestAgent, 
        token_counter: TokenCounter,
        max_messages: int = 20, 
        keep_front_messages: int = 3,
        max_tool_calls: int = 3, 
        max_tokens: int = 20000
    ) -> None:
        self.llm_client = llm_client
        self.token_counter = token_counter
        self.max_messages = max_messages
        self.keep_front_messages = keep_front_messages
        self.max_tool_calls = max_tool_calls
        self.max_tokens = max_tokens

    def _trim_chats(self, history: list[Message]):
        snipped = len(history) - self.max_messages
        snipped_message = Message(
            role="user",
            content=f"[已跳过 {snipped} 条历史消息]",
        )
        history[:] = (
            history[: self.keep_front_messages]
            + [snipped_message]
            + history[-(self.max_messages - self.keep_front_messages - 1) :]
        )

    def _trim_tools(self, history: list[Message]):
        tool_indices = [i for i, msg in enumerate(history) if msg.role == "tool"][:-self.max_tool_calls]
        for idx in tool_indices:
            history[idx].content = "[该工具结果已压缩，如需详情请重新调用]"
        
    def _llm_summary(self, history: list[Message]):
        messages_to_summary = "".join([f"[{msg.role}]: {msg.content}\n" for msg in history])[:100000]

        messages = [
            {"role": "system", "content": SUMMARY_PROMPT}, 
            {"role": "user", "content": "以下是对话历史：\n\n" + messages_to_summary}
        ]
        response = self.llm_client.invoke(messages=messages)
        snipped_message = Message(
            role="user",
            content="[Compacted]\n\n"+ response.content,
        )

        history[:] = [snipped_message]

    def compact(self, history: list[Message]):
        # TODO: might add reactive_compact(self)
        if len(history) > self.max_messages:
            self._trim_chats(history=history)
        
        if len([msg for msg in history if msg.role=="tool"]) > self.max_tool_calls:
            self._trim_tools(history=history)

        tokens = self.token_counter.count(history)
        if tokens > self.max_tokens:
            self._llm_summary(history=history)
