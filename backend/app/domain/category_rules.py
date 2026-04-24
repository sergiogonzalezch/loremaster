from app.models.entities import EntityType
from app.models.enums import ContentCategory

ENTITY_CATEGORY_MAP: dict[EntityType, list[ContentCategory]] = {
    EntityType.character: [
        ContentCategory.backstory,
        ContentCategory.extended_description,
        ContentCategory.scene,
        ContentCategory.chapter,
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


def validate_category_for_entity(
    entity_type: EntityType, category: ContentCategory
) -> bool:
    return category in ENTITY_CATEGORY_MAP[entity_type]
