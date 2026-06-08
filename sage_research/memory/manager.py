import json
import os

from .working_memory import WorkingMemory
from .semantic_memory import SemanticMemory, INDEX_FILE
from ..base.llm_client import TestAgent


CONSOLIDATE_PROMPT = (
    "<role>\n"
    "你是一个记忆管理助手，负责为记忆条目生成结构化的元数据。\n"
    "</role>\n\n"
    "<goal>\n"
    "为用户提供的每条记忆内容生成对应的name和description。\n"
    "</goal>\n\n"
    "<instructions>\n"
    "- name: 简短的英文kebab-case命名，2-4个词\n"
    "- description: 一句话中文描述，概括记忆的核心内容，用于快速检索\n"
    "- 使用generate_memory_metadata工具返回结果\n"
    "</instructions>\n\n"
    "<output_format>\n"
    "通过generate_memory_metadata工具调用返回，每条记忆对应一个name和description。\n"
    "</output_format>\n\n"
    "<example>\n"
    "记忆内容: 用户喜欢用Python写爬虫，常用requests和BeautifulSoup库\n"
    "name: python-scraping-preference\n"
    "description: 用户偏好使用Python的requests和BeautifulSoup进行网页爬取\n"
    "</example>"
)

memory_schema = {
    "type": "function",
    "function": {
        "name": "generate_memory_metadata",
        "description": "为每条记忆生成名称和描述",
        "parameters": {
            "type": "object",
            "properties": {
                "memories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "kebab-case英文短名",
                            },
                            "description": {
                                "type": "string",
                                "description": "一句话中文描述",
                            },
                        },
                        "required": ["name", "description"],
                    },
                }
            },
            "required": ["memories"],
        },
    },
}


class MemoryManager:
    def __init__(self, working_memory, semantic_memory, llm_client) -> None:
        self.working_memory: WorkingMemory = working_memory
        self.semantic_memory: SemanticMemory = semantic_memory
        self.llm_client: TestAgent = llm_client

    def get_semantic_index(self) -> str:
        file_path = os.path.join(self.semantic_memory.config.storage_dir, INDEX_FILE)

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            text = ""

        return text

    def retrieve(self, query: str, top_k: int = 5) -> str:
        working_list = self.working_memory.retrieve(query=query, top_k=top_k)
        semantic_list = self.semantic_memory.retrieve(query=query, top_k=top_k)
        total_list = working_list + semantic_list
        lines = []

        for memory in total_list:
            if memory.name:
                lines.append(f"- [{memory.name}]: {memory.description}\n")
            else:
                lines.append(f"- {memory.content}\n")

        return "## Memories\n\n" + "".join(lines)

    def add_to_working(self, content: str, importance: float):
        self.working_memory.add(content=content, importance=importance)

    def add_to_semantic(
        self, content: str, importance: float, name: str, description: str
    ):
        self.semantic_memory.add(
            content=content,
            importance=importance,
            name=name,
            description=description,
        )

    def forget(self):
        self.working_memory.forget()
        self.semantic_memory.forget()

    def consolidate(self, importance_threshold: float = 0.7):
        important_memories = [
            exsisting_memory
            for exsisting_memory in self.working_memory.get_all()
            if exsisting_memory.importance > importance_threshold
        ]
        if not important_memories:
            return

        # llm-generated memory names and descriptions
        content = "为以下每条记忆内容生成一个简短的英文名(kebab-case)和一句话中文描述: "
        for i, important_memory in enumerate(important_memories):
            content += f"\n{i+1}. {important_memory.content}\n"

        messages = [
            {"role": "system", "content": CONSOLIDATE_PROMPT},
            {"role": "user", "content": content},
        ]
        result = self.llm_client.invoke(messages=messages, tools=[memory_schema])
        memories = json.loads(result.tool_calls[0].function.arguments)["memories"]

        for important_memory, memory_metadata in zip(important_memories, memories):
            self.semantic_memory.add(
                content=important_memory.content,
                name=memory_metadata["name"],
                description=memory_metadata["description"],
                importance=important_memory.importance
            )
            self.working_memory.remove_one(important_memory.id)
