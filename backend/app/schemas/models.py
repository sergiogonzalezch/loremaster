from pydantic import BaseModel
from fastapi import UploadFile, File

class GenerateTextRequest(BaseModel):
    query: str

# class IngestDocumentRequest(BaseModel):
#     file: UploadFile = File(...)

class CreateEntityRequest(BaseModel):
    name: str
    description: str = ""