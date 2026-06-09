from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float | None = None
    source: str

    def __str__(self) -> str:
        return f"Title: {self.title}\nURL: {self.url}\nContent: {self.content}"
