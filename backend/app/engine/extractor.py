"""Extracción de texto desde archivos PDF y TXT.

Implementa extracción de texto plano con protección contra PDF bombs:
límite de páginas configurable via max_pdf_pages en Settings.
"""

import io

from pypdf import PdfReader

from app.core.config import settings


def extract_text(content_bytes: bytes, content_type: str) -> str:
    """Extrae texto plano desde bytes según el tipo de contenido.

    Soporta 'application/pdf' y 'text/plain'. Lanza ValueError para tipos no soportados.

    Para PDFs, valida el límite de páginas para prevenir
    PDF bombs (archivos PDF con miles de páginas que causan OOM).

    Args:
        content_bytes: Contenido binario del archivo.
        content_type: Tipo MIME del archivo (application/pdf o text/plain).

    Returns:
        Texto extraído del documento.

    Raises:
        ValueError: Si el tipo no es soportado, o si el PDF excede max_pdf_pages.

    """
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content_bytes))
        if len(reader.pages) > settings.max_pdf_pages:
            msg = f"El PDF excede el límite de {settings.max_pdf_pages} páginas"
            raise ValueError(
                msg,
            )
        return "\n".join(page.extract_text() or "" for page in reader.pages[: settings.max_pdf_pages])
    if content_type == "text/plain":
        return content_bytes.decode("utf-8", errors="ignore")
    msg = f"Unsupported content type: {content_type}"
    raise ValueError(msg)
