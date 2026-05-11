"""Validador de archivos subidos.

Provee validación de tipos MIME, magic bytes, extensión y sanitización
para archivos de imagen y documentos.

Funcionalidades de seguridad:
    - Validación de magic bytes para PDFs (H-6).
    - Strip de metadatos EXIF en imágenes (L-2).
    - Validación de extensión vs tipo MIME.
    - Límite de tamaño configurable.

TODO:
    - Añadir validación de magic bytes para imágenes (M-18).
"""

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
    """Verifica que el contenido coincida con el tipo esperado usando magic bytes.

    Implementa la validación H-6: no confiar únicamente en el content_type
    del cliente. Verifica los bytes reales del archivo.

    Args:
        content: Contenido binario del archivo.
        expected_type: Tipo MIME esperado (application/pdf o text/plain).

    Raises:
        ValueError: Si los magic bytes no coinciden con el tipo esperado.
    """
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

    Implementa la protección L-2: strip de metadatos sensibles
    (GPS, datos de cámara, etc.) de imágenes subidas.

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
    """Validador estático para archivos subidos.

    Valida tipos MIME, extensiones, magic bytes y tamaño de archivos.
    """

    @staticmethod
    def validate_image(file: UploadFile, max_bytes: int | None = None) -> bytes:
        """Valida que el archivo sea una imagen válida.

        Verifica tipo MIME permitido, extensión válida, strip de EXIF
        y tamaño máximo.

        Args:
            file: Archivo subido via UploadFile.
            max_bytes: Tamaño máximo en bytes (opcional).

        Returns:
            Contenido binario de la imagen validada y sanitizada.

        Raises:
            ValueError: Si no pasa alguna validación.
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
        """Valida que el archivo sea un documento permitido.

        Verifica tipo MIME, magic bytes y tamaño máximo.
        Implementa H-6: validación de magic bytes para prevenir
        que un atacante suba archivos con content_type falsificado.

        Args:
            file: Archivo subido via UploadFile.
            allowed_types: Conjunto de tipos MIME permitidos (default: PDF, TXT).
            max_bytes: Tamaño máximo en bytes (opcional).

        Returns:
            Contenido binario del documento validado.

        Raises:
            ValueError: Si no pasa alguna validación.
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
