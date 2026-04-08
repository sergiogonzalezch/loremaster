from pydantic import BaseModel, Field
from typing import Dict


class GenerateTextRequest(BaseModel):
    query: str = Field(
        ..., min_length=5, description="Pregunta o consulta para generar texto."
    )


class GenerateTextResponse(BaseModel):
    answer: str = Field(..., description="Texto generado en respuesta a la consulta.")
    source: Dict = Field(..., description="Fuente utilizada para generar la respuesta.")
    query: str = Field(..., description="Consulta original enviada por el usuario.")
