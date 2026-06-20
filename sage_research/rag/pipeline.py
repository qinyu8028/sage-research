import json
import os
from datetime import datetime

from .vector_store import VectorStore
from .reranker import Reranker
from .chunker import TextChunker
from .embedding import Embedding
from .document import Document, Chunk
from .mqe import MQE
from ..base import LLMClient


INGEST_PROMPT = """你是一个知识库管理助手。你需要判断搜索结果是否包含有价值的知识内容，值得保存到本地知识库中。

判断标准:
- 值得保存: 包含具体的技术概念、原理解释、方法论、数据或事实，有长期参考价值
- 不值得保存: 内容过于笼统、重复常识、是广告或导航页、与查询主题无关、信息不可靠

如果值得保存，请将搜索结果中的有价值内容提炼整合为结构清晰的知识摘要，使用"小节标题+内容"的格式，去除重复和无关内容。

示例输出格式:

查询: BM25算法原理

摘要:
## BM25算法

### 核心思想
BM25(Best Matching 25)是一种基于概率模型的排序函数，用于估算文档与查询的相关性。它是TF-IDF的改进版本，引入了文档长度归一化和词频饱和机制。

### 计算公式
对查询中的每个词，BM25计算: score(D,Q) = IDF(q) * (tf * (k1+1)) / (tf + k1 * (1 - b + b * dl/avgdl))
- k1: 词频饱和参数，通常取1.2-2.0
- b: 文档长度归一化参数，通常取0.75
- dl/avgdl: 当前文档长度与平均文档长度的比值

### 与TF-IDF的区别
TF-IDF中词频线性增长，出现10次的权重是1次的10倍。BM25引入饱和曲线，词频增长到一定程度后边际收益递减，更符合实际的相关性判断。"""


ingest_schema = {
    "type": "function",
    "function": {
        "name": "evaluate_search_results",
        "description": "评估搜索结果的价值并生成知识摘要",
        "parameters": {
            "type": "object",
            "properties": {
                "worth_saving": {
                    "type": "boolean",
                    "description": "搜索结果是否值得保存。true表示值得，false表示不值得",
                },
                "summary": {
                    "type": "string",
                    "description": "提炼后的知识摘要。worth_saving为false时填空字符串",
                },
            },
            "required": ["worth_saving", "summary"],
        },
    },
}


class Pipeline:
    VECTOR_STORE_FILE = "vector_store.json"
    DOCUMENTS_DIR = "documents"
    SEARCH_CACHE_DIR = "search_cache"

    def __init__(
        self, data_dir: str, llm_client: LLMClient | None = None, mqe: MQE | None = None
    ) -> None:
        self.chunker = TextChunker()
        self.reranker = Reranker()
        self.embedding = Embedding()
        self.llm_client = llm_client
        self.data_dir = data_dir
        self.mqe = mqe

        os.makedirs(os.path.join(data_dir, self.DOCUMENTS_DIR), exist_ok=True)
        os.makedirs(os.path.join(data_dir, self.SEARCH_CACHE_DIR), exist_ok=True)

        store_path = os.path.join(data_dir, self.VECTOR_STORE_FILE)
        self.vector_store = (
            VectorStore.load_json(store_path)
            if os.path.exists(store_path)
            else VectorStore()
        )

    def add_document(self, file_path: str, save: bool = True):
        document = Document.read_file(file_path)
        chunks = self.chunker.chunk(document)
        text_chunks = [chunk.content for chunk in chunks]
        embedding_list, tokens = self.embedding.invoke(text_chunks)

        for ebd, chunk in zip(embedding_list, chunks):
            chunk.embedding = ebd

        self.vector_store.add_chunks(chunks)
        if save:
            self.save()

    def add_text(self, text: str, query: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in query[:20] if c.isalnum() or c in "_ -")
        file_name = f"{timestamp}_{safe_query}.md"
        file_path = os.path.join(self.data_dir, self.SEARCH_CACHE_DIR, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        self.add_document(file_path)

    def save(self):
        store_path = os.path.join(self.data_dir, self.VECTOR_STORE_FILE)
        self.vector_store.save_to_json(store_path)

    def retrieve(self, query: str, top_k: int = 5) -> str:
        if not self.mqe:
            query_embedding, query_tokens = self.embedding.invoke(query)

            retrieved = self.vector_store.hybrid_search(
                query=query, query_embedding=query_embedding, top_k=top_k * 4
            )

            chunks = [chunk for chunk, score in retrieved]

            rerank_results = self.reranker.rerank(query=query, chunks=chunks, top_k=top_k)
            text = ""
            for i, (chunk, score) in enumerate(rerank_results):
                text += f"[{i+1}] {chunk.content}\n"

            return text
        
        else:
            query_list = self.mqe.generate_multiple_query(query)
            result: dict[tuple[str, int], tuple[Chunk, float]] = {}

            for sub_query in query_list:
                query_embedding, query_tokens = self.embedding.invoke(sub_query)

                retrieved = self.vector_store.hybrid_search(
                    query=sub_query, query_embedding=query_embedding, top_k=top_k * 4
                )

                for chunk, score in retrieved:
                    if (chunk.file_path, chunk.chunk_idx) not in result:
                        result[(chunk.file_path, chunk.chunk_idx)] = (chunk, score)
                    else:
                        result[(chunk.file_path, chunk.chunk_idx)] = (
                            chunk, 
                            result[(chunk.file_path, chunk.chunk_idx)][1] + score
                        )
            
            sorted_results = sorted(result.values(), key=lambda x: x[1], reverse=True)[:top_k * 4]
            candidate_chunks = [chunk for chunk, score in sorted_results]
            rerank_results = self.reranker.rerank(query=query, chunks=candidate_chunks, top_k=top_k)
            text = ""
            for i, (chunk, score) in enumerate(rerank_results):
                text += f"[{i+1}] {chunk.content}\n"

            return text

    def ingest_search_results(self, query: str, search_content: str):
        if self.llm_client is None:
            raise RuntimeError("ingest_search_results 需要 llm_client，但未提供")

        messages = [
            {"role": "system", "content": INGEST_PROMPT}, 
            {"role": "user", "content": f"查询: {query}\n\n搜索结果:\n{search_content}"}
        ]

        response = self.llm_client.invoke(messages=messages, tools=[ingest_schema])
        parameters = json.loads(response.tool_calls[0].function.arguments)

        if parameters["worth_saving"]:
            self.add_text(text=parameters["summary"], query=query)