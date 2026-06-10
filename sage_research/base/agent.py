from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .message import Message
from .config import Config
from .llm_client import TestAgent as llm_client

if TYPE_CHECKING:
    from ..context.context_builder import ContextBuilder


class AgentBase(ABC):
    """
    Agent 基类
    - name: 单Agent项目可以省掉, 多Agent时才需要
    - system_prompt: 可以写死在子类里, 不一定要从外部传入
    - config: 前期可以直接硬编码参数, 后期再抽成Config
    """

    def __init__(
        self,
        name: str,
        llm: llm_client,
        context_builder: ContextBuilder,
        system_prompt: str | None = None,
        config: Config | None = None,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config
        self.context_builder = context_builder

        self._history: list[Message] = []

    @abstractmethod
    def run(self, prompt: str, **kwags) -> str:
        pass

    def _build_messages(self, system_prompt: str | None = None) -> list[dict[str, str]]:
        prompt = system_prompt or self.system_prompt

        messages = self.context_builder.build_context(
            system_prompt=prompt, history=self._history
        )

        return messages

    def add_message(self, message: Message):
        self._history.append(message)

    def clear_history(self):
        self._history.clear()

    def get_history(self):
        return self._history.copy()

    def __str__(self):
        return f"Agent(name={self.name}, model={self.llm.model})"
