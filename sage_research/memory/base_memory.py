import uuid

from abc import ABC, abstractmethod
from typing import Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


MemoryType = Literal["working", "episodic", "semantic", "procedural"]


class WorkingMemoryConfig(BaseModel):
    capacity: int = 20
    ttl_minutes: int = 60
    importance_threshold: float = 0.1


class SemanticMemoryConfig(BaseModel):
    capacity: int = 20
    importance_threshold: float = 0.1
    storage_dir: str


class MemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    memory_type: MemoryType
    importance: float | None = 0.5
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    name: str | None = None
    description: str | None = None


class MemoryBase(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def retrieve(self, query: str, top_k: int) -> list[MemoryItem]:
        pass

    @abstractmethod
    def remove_one(self, id_to_remove: str) -> MemoryItem:
        pass

    @abstractmethod
    def add(self, content: str, importance: float = 0.5):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def forget(self):
        pass

    @abstractmethod
    def get_all(self):
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        pass
