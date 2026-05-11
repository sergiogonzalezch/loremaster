"""Extracción de texto desde archivos PDF y TXT."""

import io

from pypdf import PdfReader

from app.core.config import settings


def extract_text(content_bytes: bytes, content_type: str) -> str:
    """Extrae texto plano desde bytes según el tipo de contenido.

    Soporta 'application/pdf' y 'text/plain'. Lanza ValueError para tipos no soportados.
    """
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content_bytes))
        if len(reader.pages) > settings.max_pdf_pages:
            raise ValueError(
                f"El PDF excede el límite de {settings.max_pdf_pages} páginas"
            )
        return "\n".join(
            page.extract_text() or "" for page in reader.pages[: settings.max_pdf_pages]
        )
    if content_type == "text/plain":
        return content_bytes.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported content type: {content_type}")
