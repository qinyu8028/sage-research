from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


MessageRole = Literal["user", "assistant", "system", "tool"]


class Message(BaseModel):
    content: str | None = None
    role: MessageRole
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] | None = Field(default_factory=dict)

    def to_dict(self):
        result = {"role": self.role, "content": self.content}
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result

    def __str__(self):
        if self.tool_calls:
            calls = [
                f'{tc["function"]["name"]}({tc["function"]["arguments"]})'
                for tc in self.tool_calls
            ]
            return f"[{self.role}] tool call: {', '.join(calls)}"

        return f"[{self.role}] {self.content}"
