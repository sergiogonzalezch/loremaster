from pydantic import BaseModel

class GenerateTextRequest(BaseModel):
    query: str