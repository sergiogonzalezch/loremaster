class DuplicateEntityNameError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Ya existe una entidad llamada '{name}' en esta colección.")


class DuplicateCollectionNameError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Ya existe una colección llamada '{name}'.")


class ContentNotAllowedError(Exception):
    def __init__(self, message: str = "Contenido no permitido.") -> None:
        super().__init__(message)


class NoContextAvailableError(Exception):
    def __init__(self) -> None:
        super().__init__("No hay contexto disponible para responder esta consulta.")


class PendingLimitExceededError(Exception):
    pass


class UnsupportedFileTypeError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class MissingFilenameError(Exception):
    pass


class DocumentExtractionError(Exception):
    pass


class DatabaseError(Exception):
    pass


class InvalidCategoryError(Exception):
    def __init__(self, category: str, entity_type: str) -> None:
        super().__init__(
            f"La categoría '{category}' no es válida para el tipo de entidad '{entity_type}'."
        )


class VectorStoreError(Exception):
    pass


class ContentDiscardedError(Exception):
    def __init__(self) -> None:
        super().__init__("El contenido está descartado y no puede editarse.")


class GeneratedContentBlockedError(Exception):
    def __init__(self) -> None:
        super().__init__("El contenido generado no está permitido.")
