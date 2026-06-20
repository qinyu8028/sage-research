from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_idx: int
    content: str
    file_path: str
    embedding: list[float] | None = None
    tokens: list[str] | None = None
    

class Document(BaseModel):
    file_path: str
    text: str

    @classmethod
    def read_file(cls, file_path: str) -> Document:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        return cls(file_path=file_path, text=text)