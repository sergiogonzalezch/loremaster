"""Enumeraciones para categorías de contenido y estados del ciclo de vida."""

from enum import StrEnum


class ContentCategory(StrEnum):
    """Categorías de contenido que pueden generarse para una entidad.

    Attributes:
        backstory: Historia y origen del personaje/facción/criatura/ítem.
        extended_description: Descripción detallada de apariencia, comportamiento, etc.
        scene: Escena narrativa ambientada en el mundo.

    """

    backstory = "backstory"
    extended_description = "extended_description"
    scene = "scene"


class ContentStatus(StrEnum):
    """Estados del ciclo de vida de un contenido generado.

    Attributes:
        pending: Contenido recién generado, pendiente de revisión.
        confirmed: Contenido revisado y aprobado por el usuario.
        discarded: Contenido rechazado o descartado tras confirmación de otro.

    """

    pending = "pending"
    confirmed = "confirmed"
    discarded = "discarded"
