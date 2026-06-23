from typing import Literal
from pydantic import BaseModel


class ClarifyRequest(BaseModel):
    query: str


class ClarifyResult(BaseModel):
    is_clear: bool
    brief: str | None = None
    directions: list[str] = []
    message: str | None = None


class RefineRequest(BaseModel):
    query: str
    response: str


class RefineResult(BaseModel):
    brief: str


class ResearchRequest(BaseModel):
    brief: str


class SaveReportRequest(BaseModel):
    title: str
    content: str


class IngestRequest(BaseModel):
    src: str
    custom_title: str | None = None
    overwrite: bool = True


class IngestResult(BaseModel):
    title: str
    status: Literal["skipped", "overwritten", "created"]