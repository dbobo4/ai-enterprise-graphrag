from typing import Literal, NotRequired

from typing_extensions import TypedDict


SearchMode = Literal["standard", "multi-step", "graph"]
EvidenceStatus = Literal["complete", "partial", "missing", "insufficient", "unsupported", "error"]


class Source(TypedDict):
    source: str
    chunk: int
    reference: str
    snippet: str


class SourcesEvent(TypedDict):
    type: Literal["sources"]
    sources: list[Source]
    top_k: int


class TokenEvent(TypedDict):
    type: Literal["token"]
    text: str


class DoneEvent(TypedDict):
    type: Literal["done"]


class ErrorEvent(TypedDict):
    type: Literal["error"]
    message: str


ChatEvent = SourcesEvent | TokenEvent | DoneEvent | ErrorEvent


class Calls(TypedDict):
    llm: int
    vector_searches: int
    graph_queries: int


class Answer(TypedDict):
    answer: str
    sources: list[Source]
    top_k: int
    status: EvidenceStatus
    calls: Calls
    note: NotRequired[str | None]


class SeedManifest(TypedDict):
    documents: int
    chunks: int
    top_k: int
    fingerprint: str
