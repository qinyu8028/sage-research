import warnings
from typing import TYPE_CHECKING

from .history_compactor import HistoryCompactor
from .token_counter import TokenCounter
from .truncator import Truncator
from ..base import Message

if TYPE_CHECKING:
    from ..memory.manager import MemoryManager


class ContextBuilder:
    def __init__(
        self, 
        history_compactor: HistoryCompactor, 
        token_counter: TokenCounter, 
        truncator: Truncator, 
        reserve_ratio: float = 0.15, 
        max_tokens: int = 30000, 
        memory_manager: MemoryManager | None = None,
    ) -> None:
        self.history_compactor = history_compactor
        self.token_counter = token_counter
        self.truncator = truncator
        self.reserve_ratio = reserve_ratio
        self.max_tokens = max_tokens
        self.memory_manager = memory_manager

    def build_context(
        self, 
        system_prompt: str, 
        history: list[Message]
    ) -> list[dict[str, str]]:

        # add memory
        if self.memory_manager:
            semantic_memory_index = self.memory_manager.get_semantic_index()
            if semantic_memory_index:
                system_prompt += "\n\n## 长期记忆索引\n" + semantic_memory_index
            
            user_queries = [message.content for message in history if message.role == "user"]
            if user_queries:
                user_query = user_queries[-1]
                memory_context = self.memory_manager.retrieve(query=user_query)
                system_prompt += "\n\n## 记忆检索结果\n" + memory_context
        
        system_tokens = self.token_counter.count(system_prompt)
        history_budget = max(0, self.max_tokens * (1 - self.reserve_ratio) - system_tokens)
        history_tokens = self.token_counter.count(history)

        # truncate tool results
        if history_tokens > history_budget:
            for msg in history:
                if msg.role == "tool":
                    msg.content = self.truncator.truncate(msg.content)

            # use llm to compact history
            history_tokens = self.token_counter.count(history)
            if history_tokens > history_budget:
                self.history_compactor.compact(history)

                # still too long
                history_tokens = self.token_counter.count(history)
                if history_tokens > history_budget:
                    warnings.warn(
                        f"上下文仍超出预算: {history_tokens}/{history_budget} tokens. 请检查 system prompt 以及 max_tokens 设置。"
                    )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append(msg.to_dict())

        return messages