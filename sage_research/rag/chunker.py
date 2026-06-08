from .document import Document, Chunk


class TextChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> list[Chunk]:
        """包装 list[str] -> list[Chunk]"""
        splits = self._split_text(document.text)
        chunks = []
        for idx, text_split in enumerate(splits):
            chunk = Chunk(
                chunk_idx=idx, content=text_split, file_path=document.file_path
            )
            chunks.append(chunk)

        return chunks

    def _split_text(self, text: str, sep_level: int = 0) -> list[str]:
        """recursively split the text"""
        separators = ["\n\n", "\n", "。", ".", " "]
        if len(text) <= self.chunk_size:
            return [text]

        elif sep_level >= len(separators):
            splits = []
            for i in range(len(text) // self.chunk_size):
                splits.append(text[i * self.chunk_size : (i + 1) * self.chunk_size])
            if text[(i + 1) * self.chunk_size :]:
                splits.append(text[(i + 1) * self.chunk_size :])
            return splits

        else:
            parts = text.split(separators[sep_level])
            splits = []
            small_splits = []
            for part in parts:
                if len(part) > self.chunk_size:
                    splits.extend(self._merge_splits(splits=small_splits))
                    small_splits = []
                    splits.extend(self._split_text(text=part, sep_level=sep_level + 1))
                else:
                    small_splits.append(part)

            # the rest of small_splits
            splits.extend(self._merge_splits(splits=small_splits))

            return splits

    def _merge_splits(self, splits: list[str]) -> list[str]:
        """merge and overlap"""
        if not splits:
            return []

        buffer = []
        total_len = 0
        merge_split = []

        for split_text in splits:
            if total_len + len(split_text) > self.chunk_size:
                merge_split.append("".join(buffer))
                while total_len > self.chunk_overlap:
                    popped_split = buffer.pop(0)
                    total_len -= len(popped_split)

            buffer.append(split_text)
            total_len += len(split_text)

        if buffer:
            merge_split.append("".join(buffer))

        return merge_split
