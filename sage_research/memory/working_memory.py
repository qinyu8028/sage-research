import jieba
from rank_bm25 import BM25Okapi
from typing import Any
from datetime import datetime

from .base_memory import MemoryBase, MemoryItem, WorkingMemoryConfig


class WorkingMemory(MemoryBase):
    def __init__(self, config: WorkingMemoryConfig):
        super().__init__(config)
        self.memories: list[MemoryItem] = []
        self.config: WorkingMemoryConfig  # to ensure automated highlights

    def add(self, content: str, importance: float = 0.5):
        memory = MemoryItem(
            content=content, memory_type="working", importance=importance
        )
        if len(self.memories) >= self.config.capacity:
            min_score = float("inf")
            for idx, history_memory in enumerate(self.memories):
                time_decay = self._calculate_time_decay(history_memory)
                score = history_memory.importance * time_decay

                if score < min_score:
                    min_score = score
                    min_idx = idx

            self.memories.pop(min_idx)

        self.memories.append(memory)

    def remove_one(self, id_to_remove: str) -> MemoryItem:
        removed = None
        for idx, history_memory in enumerate(self.memories):
            if history_memory.id == id_to_remove:
                removed = self.memories.pop(idx)
                break

        return removed

    def retrieve(self, query: str, top_k: int) -> list[MemoryItem]:
        if not self.memories:
            return []

        # word segmentation
        corpus = [memory.content for memory in self.memories]
        segmented_corpus = [jieba.lcut(string) for string in corpus]

        segmented_query = jieba.lcut(query)

        # calculate bm25 score
        bm25 = BM25Okapi(segmented_corpus)
        bm25_scores = bm25.get_scores(segmented_query)

        # calculate total scores
        total_scores = []
        for bm25_score, memory in zip(bm25_scores, self.memories):
            importance = memory.importance
            time_decay = self._calculate_time_decay(memory)
            total_score = bm25_score * (0.8 + importance * 0.4) * time_decay

            total_scores.append(total_score)

        # sorted() returns a new list, .sort() operates directly on the original list.
        memory_list = list(zip(self.memories, total_scores))
        sorted_memory_list = sorted(memory_list, key=lambda x: x[1], reverse=True)
        sorted_memories = [pair[0] for pair in sorted_memory_list]

        return sorted_memories[:top_k]

    def _calculate_time_decay(self, memory: MemoryItem) -> float:
        secs = (datetime.now() - memory.timestamp).total_seconds()
        hours = secs / 3600
        return max(0.1, 0.95 ** (hours / 6))

    def clear(self):
        self.memories = []

    def get_all(self) -> list[MemoryItem]:
        return self.memories.copy()

    def forget(self):
        # delete outdated memories
        self.memories = [
            m
            for m in self.memories
            if (datetime.now() - m.timestamp).total_seconds() / 60
            <= self.config.ttl_minutes
        ]
        # delete least important memories
        self.memories = [
            m for m in self.memories if m.importance >= self.config.importance_threshold
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "memory_length": len(self.memories),
            "capacity": self.config.capacity,
            "importance_threshold": self.config.importance_threshold,
        }
