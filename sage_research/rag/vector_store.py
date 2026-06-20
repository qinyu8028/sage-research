import math

import json
import jieba
from rank_bm25 import BM25Okapi

from .document import Chunk


class VectorStore:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self._file_index: dict[str, list[Chunk]] = {}

    def add_chunks(self, chunks: list[Chunk]):
        for chunk in chunks:
            if chunk.tokens is None:
                chunk.tokens = jieba.lcut(chunk.content)
            self.chunks.append(chunk)
            self._file_index.setdefault(chunk.file_path, []).append(chunk)

    def cosine_search(
        self, query_embedding: list[float], top_k: int
    ) -> list[tuple[Chunk, float]]:
        score_pairs = []
        mod_query = math.sqrt(sum(x**2 for x in query_embedding))

        for chunk in self.chunks:
            ebd = chunk.embedding
            dot = 0
            for qi, ei in zip(query_embedding, ebd):
                dot += qi * ei
            mod_ebd = math.sqrt(sum(x**2 for x in ebd))
            cosine_score = dot / (mod_query * mod_ebd)
            score_pairs.append((chunk, cosine_score))

        score_pairs = sorted(score_pairs, key=lambda x: x[1], reverse=True)

        return score_pairs[:top_k]

    def bm25_search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        bm25 = BM25Okapi([chunk.tokens for chunk in self.chunks])
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

    def remove_by_filepath(self, file_path: str) -> int:
        if file_path not in self._file_index:
            return 0

        count = len(self._file_index[file_path])
        self.chunks = [chunk for chunk in self.chunks if chunk.file_path != file_path]
        del self._file_index[file_path]
        
        return count