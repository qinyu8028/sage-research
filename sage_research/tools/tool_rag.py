from typing import Any

from .base_tool import BaseTool, ToolParameter
from ..rag import Pipeline


class RAGTool(BaseTool):
    def __init__(self, pipeline: Pipeline):
        super().__init__(
            name="rag_search",
            description=(
                "在本地知识库中检索信息。"
                "适用于查询知识库中已有的、相对稳定的知识内容，如已导入的技术文档、论文笔记、项目资料等。"
                "不适用于查询实时信息、最新新闻或知识库中未收录的内容。检索质量取决于已导入的文档覆盖范围。"
                "返回按相关性排序的文本片段列表，格式为 [序号] 内容。未找到相关内容时返回提示信息。"
            ),
            parameters=[ToolParameter(
                name="query",
                type="string",
                description="检索的问题或关键词，应具体明确，聚焦单一主题。例：'Transformer 注意力机制' 而非 '介绍一下深度学习的各种模型'"
            )]
        )
        self.pipeline = pipeline

    def run_tool(self, parameters: dict[str, Any]) -> str:
        query = parameters["query"]
        result = self.pipeline.retrieve(query)
        
        if not result.strip():
            return "本地知识库中未找到相关内容"
        
        return result
