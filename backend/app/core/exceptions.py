class DuplicateEntityNameError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Ya existe una entidad llamada '{name}' en esta colección.")