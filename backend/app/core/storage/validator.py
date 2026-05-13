"""Validador de archivos subidos.

Provee validación de tipos MIME, magic bytes, extensión y sanitización
para archivos de imagen y documentos.

Funcionalidades de seguridad:
    - Validación de magic bytes para PDFs (H-6).
    - Strip de metadatos EXIF en imágenes (L-2).
    - Validación de extensión vs tipo MIME.
    - Límite de tamaño configurable.

"""

from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_MIME_TYPES: set[str] = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
DOCUMENT_MIME_TYPES: set[str] = {"text/plain", "application/pdf"}

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
        if not content.startswith((b"%PDF", b"PK\x03\x04")):
            msg = "El archivo no es un PDF válido"
            raise ValueError(msg)
    elif expected_type == "text/plain":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as e:
            msg = "El archivo no es un texto válido"
            raise ValueError(msg) from e


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
    except (OSError, SyntaxError, ValueError):
        return data


class FileValidator:
    """Validador estático para archivos subidos.

    Valida tipos MIME, extensiones, magic bytes y tamaño de archivos.
    """

    @staticmethod
    def validate_image(file: UploadFile, max_bytes: int | None = None) -> bytes:
        """Valida que el archivo sea una imagen válida.

        Verifica tipo MIME permitido, extensión válida, magic bytes de imagen,
        strip de EXIF y tamaño máximo.

        Args:
            file: Archivo subido via UploadFile.
            max_bytes: Tamaño máximo en bytes (opcional).

        Returns:
            Contenido binario de la imagen validada y sanitizada.

        Raises:
            ValueError: Si no pasa alguna validación.

        """
        if file.content_type not in IMAGE_MIME_TYPES:
            msg = (
                f"Tipo de archivo no permitido: {file.content_type}. "
                f"Solo se permiten imágenes: {', '.join(sorted(IMAGE_EXTENSIONS))}"
            )
            raise ValueError(
                msg,
            )
        ext = Path(file.filename or "image.jpg").suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            msg = f"Extensión no permitida: {ext}"
            raise ValueError(msg)

        content = file.file.read()

        # Validación de magic bytes / integridad de imagen (M-18)
        try:
            img = Image.open(BytesIO(content))
            img.verify()
        except Exception as e:
            msg = "El archivo no es una imagen válida"
            raise ValueError(msg) from e

        content = _strip_exif(content)

        if max_bytes and len(content) > max_bytes:
            msg = f"El archivo excede el tamaño máximo de {max_bytes // (1024*1024)}MB"
            raise ValueError(
                msg,
            )

        file.file.seek(0)
        return content

    @staticmethod
    def validate_document(
        file: UploadFile,
        allowed_types: set[str] | None = None,
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
            msg = f"Tipo de archivo no permitido: {file.content_type}"
            raise ValueError(msg)

        content = file.file.read()
        if max_bytes and len(content) > max_bytes:
            msg = f"El archivo excede el tamaño máximo de {max_bytes // (1024*1024)}MB"
            raise ValueError(
                msg,
            )
        _verify_magic_bytes(content, file.content_type)

        file.file.seek(0)
        return content
