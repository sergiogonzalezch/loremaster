class DuplicateEntityNameError(Exception):
    """Lanzada cuando ya existe una entidad con el mismo nombre en la colección."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Ya existe una entidad llamada '{name}' en esta colección.")


class DuplicateCollectionNameError(Exception):
    """Lanzada cuando ya existe una colección con el mismo nombre para el usuario."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Ya existe una colección llamada '{name}'.")


class ContentNotAllowedError(Exception):
    """Lanzada cuando el contenido no pasa la validación de moderación."""

    def __init__(
        self, message: str = "Contenido no permitido.", snippet: str = ""
    ) -> None:
        self.snippet = snippet[:200]
        super().__init__(message)


class NoContextAvailableError(Exception):
    """Lanzada cuando no hay documentos en Qdrant para responder una consulta RAG."""

    def __init__(self) -> None:
        super().__init__("No hay contexto disponible para responder esta consulta.")


class ContentNotConfirmedError(Exception):
    """Lanzada cuando se intenta operar sobre contenido no confirmado."""

    def __init__(self) -> None:
        super().__init__(
            "El contenido indicado no existe, no está confirmado "
            "o no pertenece a esta entidad."
        )


class PendingLimitExceededError(Exception):
    """Lanzada cuando se alcanza el límite de contenidos pendientes por confirmar."""

    def __init__(self, message: str = "") -> None:
        default = (
            "Se alcanzó el límite de contenidos pendientes. "
            "Confirma o descarta contenidos antes de generar nuevos."
        )
        super().__init__(message or default)


class UnsupportedFileTypeError(Exception):
    """Lanzada cuando se intenta subir un tipo de archivo no soportado."""

    def __init__(self) -> None:
        super().__init__("Tipo de archivo no soportado.")


class FileTooLargeError(Exception):
    """Lanzada cuando el archivo excede el tamaño máximo permitido."""

    def __init__(self) -> None:
        super().__init__("El archivo excede el tamaño máximo permitido.")


class MissingFilenameError(Exception):
    """Lanzada cuando el archivo subido no tiene nombre de archivo."""

    def __init__(self) -> None:
        super().__init__("El archivo no tiene nombre.")


class DocumentExtractionError(Exception):
    """Lanzada cuando falla la extracción de texto de un documento."""

    def __init__(self) -> None:
        super().__init__("Error al extraer texto del documento.")


class DatabaseError(Exception):
    """Lanzada cuando ocurre un error en operaciones de base de datos."""

    def __init__(self) -> None:
        super().__init__("Error en la base de datos.")


class InvalidCategoryError(Exception):
    """Lanzada cuando una categoría no es válida para el tipo de entidad."""

    def __init__(self, category: str, entity_type: str) -> None:
        super().__init__(
            f"La categoría '{category}' no es válida para el tipo de entidad '{entity_type}'."
        )


class VectorStoreError(Exception):
    """Lanzada cuando ocurre un error en el almacén de vectores (Qdrant)."""

    def __init__(self) -> None:
        super().__init__("Error en el almacén de vectores.")


class ContentDiscardedError(Exception):
    """Lanzada cuando se intenta editar contenido que ya fue descartado."""

    def __init__(self) -> None:
        super().__init__("El contenido está descartado y no puede editarse.")


class ContentNotShareableError(Exception):
    """Lanzada cuando se intenta compartir contenido no confirmado."""

    def __init__(self) -> None:
        super().__init__("Solo se puede compartir contenido confirmado.")


class GeneratedContentBlockedError(Exception):
    """Lanzada cuando el contenido generado es bloqueado por moderación."""

    def __init__(self, snippet: str = "") -> None:
        self.snippet = snippet[:200]
        super().__init__("El contenido generado no está permitido.")


class DocumentNotRetryableError(Exception):
    """Lanzada cuando se intenta reintentar la ingestión de un documento no eligible."""

    def __init__(self) -> None:
        super().__init__(
            "El documento no está en estado 'failed' o no tiene texto almacenado "
            "para reintentar la ingestión."
        )


class DuplicateDocumentError(Exception):
    """Lanzada cuando se detecta un documento duplicado por su contenido."""

    def __init__(self, existing_id: str) -> None:
        self.existing_id = existing_id
        super().__init__("El contenido del documento ya existe en esta colección.")
