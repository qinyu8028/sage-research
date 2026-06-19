import logging
import os
from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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

    MAX_BATCH_SIZE = 64

    def invoke(self, input_text: list[str] | str) -> tuple[list[float], int]:
        is_single = isinstance(input_text, str)
        if is_single:
            input_text = [input_text]

        logger.info("调用 %s 向量模型, %d 条输入", self.model, len(input_text))

        all_embeddings = []
        total_tokens = 0
        for i in range(0, len(input_text), self.MAX_BATCH_SIZE):
            batch = input_text[i : i + self.MAX_BATCH_SIZE]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            total_tokens += response.usage.total_tokens
            all_embeddings.extend(item.embedding for item in response.data)

        return (all_embeddings[0] if is_single else all_embeddings, total_tokens)
