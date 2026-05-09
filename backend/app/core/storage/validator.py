from pathlib import Path
from typing import Set

from fastapi import UploadFile

IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
DOCUMENT_MIME_TYPES: Set[str] = {"text/plain", "application/pdf"}


class FileValidator:
    @staticmethod
    def validate_image(file: UploadFile, max_bytes: int | None = None) -> bytes:
        if file.content_type not in IMAGE_MIME_TYPES:
            raise ValueError(
                f"Tipo de archivo no permitido: {file.content_type}. "
                f"Solo se permiten imágenes: {', '.join(sorted(IMAGE_EXTENSIONS))}"
            )
        ext = Path(file.filename or "image.jpg").suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            raise ValueError(f"Extensión no permitida: {ext}")

        content = file.file.read()
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
        allowed = allowed_types or DOCUMENT_MIME_TYPES
        if file.content_type not in allowed:
            raise ValueError(f"Tipo de archivo no permitido: {file.content_type}")

        content = file.file.read()
        if max_bytes and len(content) > max_bytes:
            raise ValueError(
                f"El archivo excede el tamaño máximo de {max_bytes // (1024*1024)}MB"
            )

        file.file.seek(0)
        return content
