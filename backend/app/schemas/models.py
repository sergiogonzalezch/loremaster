from pydantic import BaseModel

class GenerateRequest(BaseModel):
    query: str
    max_tokens: int = 500