from pydantic import BaseModel
from pydantic import Field

class GenerateTextRequest(BaseModel):
    query: str
    doc_ids: list[str] | None = None
    max_tokens: int = Field(500, ge=1, le=2000)
    stream: bool = False

class SourceChunk(BaseModel):
    chunk_id: str
    doc_id: str
    score: float
    preview: str

class GenerateTextResponse(BaseModel):
    response: str
    sources: list[SourceChunk]
    model: str
    cached: bool
    token_count: int
    latency_ms: int