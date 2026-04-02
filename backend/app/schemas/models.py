from pydantic import BaseModel

class GenerateTextRequest(BaseModel):
    query: str

class IngestDocumentRequest(BaseModel):
    filename: str
    content: str

class CreateEntityRequest(BaseModel):
    name: str
    description: str = ""