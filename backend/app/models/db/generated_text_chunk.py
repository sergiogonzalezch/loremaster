"""Modelo de base de datos para chunks RAG asociados a un texto generado."""

import uuid

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlmodel import Field, SQLModel


class GeneratedTextChunk(SQLModel, table=True):
    """Fragmento de contexto RAG que contribuyó a una generación LLM.

    Cada fila representa un chunk de texto recuperado de Qdrant durante la
    generación. Permite auditar qué fragmentos exactos usó el modelo y de
    qué documentos provinieron, sin depender de arrays JSON en la tabla padre.

    Attributes:
        id: Identificador único UUID.
        generated_text_id: GeneratedText al que pertenece este chunk.
        document_id: Documento fuente (nullable — sin FK dura para sobrevivir borrados).
        chunk_text: Texto exacto del fragmento recuperado.
        position: Posición en los resultados de Qdrant (0 = más relevante).
        score: Puntuación de similitud coseno devuelta por Qdrant.

    """

    __tablename__ = "generated_text_chunks"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    generated_text_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("generated_texts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    document_id: str | None = Field(
        default=None,
        sa_column=Column(String(36), nullable=True),
    )
    chunk_text: str = Field(sa_column=Column(Text, nullable=False))
    position: int = Field(sa_column=Column(Integer, nullable=False))
    score: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
