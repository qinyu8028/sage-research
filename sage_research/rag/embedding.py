import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class Embedding:
    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        timeout: int = None,
    ):
        self.model = model or os.getenv("EMBEDDING_MODEL_ID")
        self.api_key = api_key or os.getenv("GLM_API_KEY")
        self.base_url = base_url or os.getenv("EMBEDDING_BASE_URL")
        self.timeout = timeout or int(os.getenv("EMBEDDING_TIMEOUT", 60))

        if not all([self.model, self.api_key, self.base_url]):
            raise ValueError(
                "model_id, api_key and base_url have to be predefined or given."
            )

        self.client = OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

    def invoke(self, input_text: list[str] | str) -> tuple[list[float], int]:
        is_single = isinstance(input_text, str)
        if is_single:
            input_text = [input_text]

        print(f"🧠 正在调用 {self.model} 向量模型...")

        response = self.client.embeddings.create(
            model=self.model,
            input=input_text,
        )

        total_tokens = response.usage.total_tokens
        embeddings = [item.embedding for item in response.data]

        return (embeddings[0] if is_single else embeddings, total_tokens)
