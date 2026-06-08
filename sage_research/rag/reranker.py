from .document import Chunk
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self) -> None:
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(
        self, 
        query: str, 
        chunks: list[Chunk], 
        top_k: int = 5
    ) -> list[tuple[Chunk, float]]: 
        
        scores = self.model.predict([[query, chunk.content] for chunk in chunks])

        reranked_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)

        return [(chunk, float(score)) for chunk, score in reranked_chunks[:top_k]]