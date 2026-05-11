from io import BytesIO
from pathlib import Path
from typing import Set

from fastapi import UploadFile
from PIL import Image

IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
DOCUMENT_MIME_TYPES: Set[str] = {"text/plain", "application/pdf"}

MAGIC_BYTES: dict[bytes, str] = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/pdf",
    b"text": "text/plain",
}


def _verify_magic_bytes(content: bytes, expected_type: str) -> None:
    """Verifica que el contenido coincida con el tipo esperado usando magic bytes."""
    if expected_type == "application/pdf":
        if not (content.startswith(b"%PDF") or content.startswith(b"PK\x03\x04")):
            raise ValueError("El archivo no es un PDF válido")
    elif expected_type == "text/plain":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("El archivo no es un texto válido")


def _strip_exif(data: bytes) -> bytes:
    """Elimina metadatos EXIF de una imagen.

    Args:
        data: Contenido binario de la imagen.

    Returns:
        Contenido binario sin metadatos EXIF.
    """
    try:
        img = Image.open(BytesIO(data))
        buffer = BytesIO()
        img.save(buffer, format=img.format or "JPEG")
        return buffer.getvalue()
    except Exception:
        return data


class FileValidator:
    """Validador estático para archivos subidos."""

    @staticmethod
    def validate_image(file: UploadFile, max_bytes: int | None = None) -> bytes:
        """Valida que el archivo sea una imagen válida (tipo MIME y extensión).
        Lanza ValueError si no pasa la validación.

        Lee y retorna el contenido del archivo tras la validación.
        """
        if file.content_type not in IMAGE_MIME_TYPES:
            raise ValueError(
                f"Tipo de archivo no permitido: {file.content_type}. "
                f"Solo se permiten imágenes: {', '.join(sorted(IMAGE_EXTENSIONS))}"
            )
        ext = Path(file.filename or "image.jpg").suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            raise ValueError(f"Extensión no permitida: {ext}")

        content = file.file.read()
        content = _strip_exif(content)

        if max_bytes and len(content) > max_bytes:
            raise ValueError(
                f"El archivo excede el tamaño máximo de {max_bytes // (1024*1024)}MB"
            )

        file.file.seek(0)
        return content

    @staticmethod
    def validate_document(
        file: UploadFile,
        allowed_types: Set[str] | None = None,
        max_bytes: int | None = None,
    ) -> bytes:
        """Valida que el archivo sea un documento permitido (tipo MIME).
        Lanza ValueError si no pasa la validación.

        Lee y retorna el contenido del archivo tras la validación.
        """
        allowed = allowed_types or DOCUMENT_MIME_TYPES
        if file.content_type not in allowed:
            raise ValueError(f"Tipo de archivo no permitido: {file.content_type}")

        content = file.file.read()
        if max_bytes and len(content) > max_bytes:
            raise ValueError(
                f"El archivo excede el tamaño máximo de {max_bytes // (1024*1024)}MB"
            )
        _verify_magic_bytes(content, file.content_type)

        file.file.seek(0)
        return content
