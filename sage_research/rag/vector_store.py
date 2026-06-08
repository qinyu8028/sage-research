import math

import json
import jieba
from rank_bm25 import BM25Okapi

from .document import Chunk


class VectorStore:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self._tokenized_docs: list[list[str]] = []

    def add_chunks(self, chunks: list[Chunk]):
        self.chunks.extend(chunks)
        for chunk in chunks:
            tokenized_content = jieba.lcut(chunk.content)
            self._tokenized_docs.append(tokenized_content)

    def cosine_search(
        self, query_embedding: list[float], top_k: int
    ) -> list[tuple[Chunk, float]]:
        scores = []
        mod_query = math.sqrt(sum(x**2 for x in query_embedding))

        for chunk in self.chunks:
            ebd = chunk.embedding
            dot = 0
            for qi, ei in zip(query_embedding, ebd):
                dot += qi * ei
            mod_ebd = math.sqrt(sum(x**2 for x in ebd))
            cosine_score = dot / (mod_query * mod_ebd)
            scores.append((chunk, cosine_score))

        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def bm25_search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        bm25 = BM25Okapi(self._tokenized_docs)
        bm25_scores = bm25.get_scores(jieba.lcut(query))
        scores = []
        for chunk, bm25_score in zip(self.chunks, bm25_scores):
            scores.append((chunk, bm25_score))

        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def hybrid_search(
        self, query: str, query_embedding: list[float], top_k: int, k: int = 60
    ) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []

        bm25_result = self.bm25_search(query=query, top_k=top_k * 2)
        cosine_result = self.cosine_search(
            query_embedding=query_embedding, top_k=top_k * 2
        )
        result: dict[tuple[str, int], tuple[Chunk, float]] = {}

        for i, pair in enumerate(bm25_result):
            result[(pair[0].file_path, pair[0].chunk_idx)] = (pair[0], 1 / (k + i))
        for i, pair in enumerate(cosine_result):
            if (pair[0].file_path, pair[0].chunk_idx) in result:
                chunk, old_score = result[(pair[0].file_path, pair[0].chunk_idx)]
                score = old_score + 1 / (k + i)
                result[(pair[0].file_path, pair[0].chunk_idx)] = (chunk, score)
            else:
                result[(pair[0].file_path, pair[0].chunk_idx)] = (pair[0], 1 / (k + i))

        result = sorted(result.values(), key=lambda x: x[1], reverse=True)

        return result[:top_k]

    def save_to_json(self, file_path: str):
        chunk_dicts = [chunk.model_dump() for chunk in self.chunks]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chunk_dicts, f, ensure_ascii=False)

    @classmethod
    def load_json(cls, file_path: str) -> VectorStore:
        with open(file_path, "r", encoding="utf-8") as f:
            data: list[dict] = json.load(f)

        chunks: list[Chunk] = []
        for chunk_dict in data:
            chunk = Chunk(**chunk_dict)
            chunks.append(chunk)

        vector_store = cls()
        vector_store.add_chunks(chunks=chunks)

        return vector_store
