from ..base import AgentBase, llm_client, Message, Config
from ..context import ContextBuilder
from .prompts import WRITER_SYSTEM_PROMPT, WRITER_USER_PROMPT


class Writer(AgentBase):
    """研究流水线的最终阶段，将多条研究笔记合成为一篇结构化的 Markdown 报告。"""

    def __init__(
        self, 
        llm: llm_client, 
        context_builder: ContextBuilder, 
        name: str = "writer", 
        system_prompt: str = WRITER_SYSTEM_PROMPT, 
        config: Config | None = None
    ):
        super().__init__(name, llm, context_builder, system_prompt, config)

    def run(self, research_brief: str, clean_notes: list[str]) -> str:
        """接收研究简报和已审查通过的研究笔记，单次 LLM 调用生成最终报告。"""
        findings = "\n\n".join(
            f"<note>\n{note}\n</note>" for note in clean_notes
        )
        prompt = WRITER_USER_PROMPT.format(
            research_brief=research_brief,
            findings=findings
        )
        user_msg = Message(content=prompt, role="user")
        self._history.append(user_msg)
        messages = self._build_messages(self.system_prompt)

        writer_response = self.llm.invoke(
            messages=messages,
        )

        writer_msg = Message(content=writer_response.content, role="assistant")
        self._history.append(writer_msg)

        return writer_response.content
