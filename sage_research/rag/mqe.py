from ..base import LLMClient


SYSTEM_PROMPT_TEMPLATE = (
    "<role>\n"
    "你是一个查询分解助手，负责将用户的搜索查询拆分为多个子问题。\n"
    "</role>\n\n"
    "<goal>\n"
    "将用户查询分解为{n}个更具体的子问题，用于从知识库中检索相关信息。\n"
    "</goal>\n\n"
    "<instructions>\n"
    "- 子问题应覆盖原始查询的不同角度\n"
    "- 每个子问题必须可以独立理解，不依赖其他子问题\n"
    "</instructions>\n\n"
    "<output_format>\n"
    "每行输出一个子问题，不要编号，不要解释。\n"
    "</output_format>\n\n"
    "<example>\n"
    "用户查询: RAG和传统搜索引擎的区别\n"
    "输出:\n"
    "RAG检索增强生成的工作原理是什么\n"
    "传统搜索引擎如何处理用户查询\n"
    "RAG相比关键词检索有哪些优势\n"
    "</example>"
)


class MQE:
    def __init__(self, llm_client: LLMClient, n: int = 3):
        self.llm_client = llm_client
        self.n = n

    def generate_multiple_query(self, query: str) -> list[str]:
        query_list = [query]
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(n=self.n)
        messages = [
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": query}, 
        ]
        response = self.llm_client.invoke(messages)
        new_queries = response.content.strip().split("\n")
        new_queries = [q.strip().lstrip("0123456789.、）) ") for q in new_queries if q.strip()][:self.n]

        query_list.extend(new_queries)

        return query_list
        
