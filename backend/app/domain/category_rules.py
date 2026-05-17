"""Reglas de validación de categorías permitidas por tipo de entidad."""

from app.models.db.entity import EntityType
from app.models.enums import ContentCategory

ENTITY_CATEGORY_MAP: dict[EntityType, list[ContentCategory]] = {
    EntityType.character: [
        ContentCategory.backstory,
        ContentCategory.extended_description,
        ContentCategory.scene,
    ],
    EntityType.creature: [
        ContentCategory.backstory,
        ContentCategory.extended_description,
        ContentCategory.scene,
    ],
    EntityType.faction: [
        ContentCategory.backstory,
        ContentCategory.extended_description,
        ContentCategory.scene,
    ],
    EntityType.location: [
        ContentCategory.extended_description,
        ContentCategory.scene,
    ],
    EntityType.item: [
        ContentCategory.backstory,
        ContentCategory.extended_description,
    ],
}
"""Mapeo de tipos de entidad a las categorías de contenido que pueden generar."""


def validate_category_for_entity(
    entity_type: EntityType,
    category: ContentCategory,
) -> bool:
    """Valida que una categoría de contenido sea válida para un tipo de entidad.

    Retorna True si la categoría está permitida para el tipo de entidad dado.
    """
    return category in ENTITY_CATEGORY_MAP[entity_type]
