import os
import json
import jieba

from rank_bm25 import BM25Okapi
from datetime import datetime

from .base_memory import MemoryBase, MemoryItem, SemanticMemoryConfig


INDEX_FILE = "MEMORY.md"
MEMORY_TEMPLATE = """---
name: {name}
description: {description}
id: {id}
memory_type: {memory_type}
timestamp: {timestamp}
importance: {importance}
metadata: {metadata}
---

{content}"""


class SemanticMemory(MemoryBase):
    def __init__(self, config):
        super().__init__(config)
        self.config: SemanticMemoryConfig  # to ensure automated highlights

        os.makedirs(self.config.storage_dir, exist_ok=True)

    @property
    def length(self):
        return len([f for f in os.listdir(self.config.storage_dir) if f != INDEX_FILE])

    def add(self, content: str, name: str, description: str, importance: float = 0.5):
        memory = MemoryItem(
            content=content,
            name=name,
            description=description,
            importance=importance,
            memory_type="semantic",
        )
        storage_path = os.path.join(self.config.storage_dir, f"{memory.name}.md")

        if not os.path.exists(storage_path) and self.length >= self.config.capacity:
            min_importance = float("inf")
            for memory_file in os.listdir(self.config.storage_dir):
                if memory_file == INDEX_FILE:
                    continue
                existing_memory = self._parse_file(
                    os.path.join(self.config.storage_dir, memory_file)
                )
                if existing_memory.importance < min_importance:
                    min_importance = existing_memory.importance
                    min_file = memory_file

            os.remove(os.path.join(self.config.storage_dir, min_file))

        with open(storage_path, "w", encoding="utf-8") as f:
            text = MEMORY_TEMPLATE.format(
                name=memory.name, 
                description=memory.description,
                id=memory.id,
                memory_type=memory.memory_type,
                timestamp=memory.timestamp,
                importance=memory.importance,
                metadata=memory.metadata,
                content=memory.content,
            )
            f.write(text)

        self._rebuild_index()

    def remove_one(self, name_to_remove: str):
        os.remove(os.path.join(self.config.storage_dir, f"{name_to_remove}.md"))
        self._rebuild_index()

    def retrieve(self, query: str, top_k: int) -> list[MemoryItem]:
        memories: list[MemoryItem] = []
        for memory_file in os.listdir(self.config.storage_dir):
            if memory_file == INDEX_FILE:
                continue
            memory = self._parse_file(
                os.path.join(self.config.storage_dir, memory_file)
            )
            memories.append(memory)

        if not memories:
            return []

        # word segmentation
        corpus = [memory.content for memory in memories]
        segmented_corpus = [jieba.lcut(string) for string in corpus]

        segmented_query = jieba.lcut(query)

        # calculate bm25 score
        bm25 = BM25Okapi(segmented_corpus)
        bm25_scores = bm25.get_scores(segmented_query)

        # calculate total scores
        total_scores = []
        for bm25_score, memory in zip(bm25_scores, memories):
            importance = memory.importance
            total_score = bm25_score * (0.8 + importance * 0.4)

            total_scores.append(total_score)

        # sorted() returns a new list, .sort() operates directly on the original list.
        memory_list = list(zip(memories, total_scores))
        sorted_memory_list = sorted(memory_list, key=lambda x: x[1], reverse=True)
        sorted_memories = [pair[0] for pair in sorted_memory_list]

        return sorted_memories[:top_k]

    def clear(self):
        for memory_file in os.listdir(self.config.storage_dir):
            if memory_file == INDEX_FILE:
                continue
            os.remove(os.path.join(self.config.storage_dir, memory_file))

        self._rebuild_index()

    def get_all(self) -> list[MemoryItem]:
        memories: list[MemoryItem] = []
        for memory_file in os.listdir(self.config.storage_dir):
            if memory_file == INDEX_FILE:
                continue
            memory = self._parse_file(
                os.path.join(self.config.storage_dir, memory_file)
            )
            memories.append(memory)

        return memories

    def forget(self):
        for memory_file in os.listdir(self.config.storage_dir):
            if memory_file == INDEX_FILE:
                continue
            memory = self._parse_file(
                os.path.join(self.config.storage_dir, memory_file)
            )
            if memory.importance < self.config.importance_threshold:
                os.remove(os.path.join(self.config.storage_dir, memory_file))

        self._rebuild_index()

    def get_stats(self):
        return {
            "memory_length": self.length,
            "capacity": self.config.capacity,
            "importance_threshold": self.config.importance_threshold,
        }

    def _parse_file(self, file_path: str) -> MemoryItem:
        result = {}
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            parts = text.split("---", 2)
            content = parts[2].strip()
            result["content"] = content

            frontmatter = parts[1].split("\n")
            for line in frontmatter:
                if line == "":
                    continue
                key, value = line.split(": ", 1)
                result[key] = value
        result["metadata"] = json.loads(result["metadata"])
        memory = MemoryItem(**result)

        return memory

    def _rebuild_index(self):
        lines = []
        for memory_file in os.listdir(self.config.storage_dir):
            if memory_file == INDEX_FILE:
                continue
            memory = self._parse_file(
                os.path.join(self.config.storage_dir, memory_file)
            )
            name = memory.name
            description = memory.description
            line_text = f"- {name}: {description}\n"
            lines.append(line_text)

        file_path = os.path.join(self.config.storage_dir, INDEX_FILE)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Memory Indices\n\n")
            f.write("".join(lines))
