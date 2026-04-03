from pydantic import BaseModel
from fastapi import UploadFile, File

class GenerateTextRequest(BaseModel):
    query: str

class CreateEntityRequest(BaseModel):
    name: str
    description: str = ""