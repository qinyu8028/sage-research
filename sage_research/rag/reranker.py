import os

from torch import nn
from sentence_transformers import CrossEncoder

from .document import Chunk


class Reranker:
    DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"
    DEFAULT_MIN_SCORE = 0.5

    def __init__(
        self,
        model_name: str | None = None,
        min_score: float | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv(
            "RERANK_MODEL_ID", self.DEFAULT_MODEL
        )
        self.min_score = (
            min_score
            if min_score is not None
            else float(os.getenv("RERANK_MIN_SCORE", self.DEFAULT_MIN_SCORE))
        )
        if not 0 <= self.min_score <= 1:
            raise ValueError("RERANK_MIN_SCORE must be between 0 and 1")

        self.model = CrossEncoder(self.model_name)

    def rerank(
        self,
        query: str,
        chunks: list[Chunk],
        top_k: int = 5,
    ) -> list[tuple[Chunk, float]]:
        if not chunks:
            return []

        scores = self.model.predict(
            [[query, chunk.content] for chunk in chunks],
            activation_fn=nn.Sigmoid(),
        )

        reranked_chunks = sorted(
            zip(chunks, scores), key=lambda item: item[1], reverse=True
        )

        return [
            (chunk, float(score))
            for chunk, score in reranked_chunks
            if float(score) >= self.min_score
        ][:top_k]
