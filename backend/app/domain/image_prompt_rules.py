"""Reglas de dominio para extracción de atributos visuales para generación de imágenes.

Construye el prompt combinado que extrae tipo específico y atributos visuales del texto
en una sola llamada LLM, produciendo una lista comma-separated directamente usable
como prompt positivo para modelos de imagen (Flux, Stable Diffusion, etc.).
"""

from app.models.db.entity import EntityType
from app.models.enums import ContentCategory

_IGNORA_BY_CATEGORY: dict[ContentCategory, str] = {
    ContentCategory.extended_description: "IGNORE: narrative, motivations, history, names.",
    ContentCategory.backstory: "IGNORE: names, dates, historical events, motivations.",
    ContentCategory.scene: "IGNORE: dialogue, thoughts, emotions.",
    ContentCategory.chapter: "IGNORE: plot, development, secondary characters.",
}
"""Instrucciones de ignorado por categoría de contenido."""

_ENTITY_NAME_EN: dict[EntityType, str] = {
    EntityType.character: "character",
    EntityType.creature: "creature",
    EntityType.location: "location",
    EntityType.faction: "faction",
    EntityType.item: "item",
}
"""Nombres en inglés de cada tipo de entidad."""

_COMBINED_TYPE_OPTIONS: dict[EntityType, str] = {
    EntityType.character: "human, alien, robot, android, cyborg, demon, angel, beast, mythical creature",
    EntityType.creature: "dragon, beast, spirit, demon, angel, mythological being, monster, animal, insect, plant",
    EntityType.location: "city, fortress, temple, forest, mountain, ruin, ship, planet, dimension",
    EntityType.faction: "kingdom, clan, brotherhood, order, guild, corporation, religion, movement",
    EntityType.item: "sword, bow, wand, shield, armor, relic, artifact, orb, sphere, jewelry, amulet, potion",
}
"""Opciones de tipo específico por entidad para el prompt combinado."""

_ATTRIBUTOS_BY_ENTITY_CATEGORY: dict[tuple[EntityType, ContentCategory], str] = {
    (EntityType.character, ContentCategory.extended_description): (
        "colors, materials, body shapes, textures, sizes, clothing, accessories, equipment, "
        "marks, distinctive details, facial expressions, posture, physical conditions, items carried, "
        "surrounding environment mentioned"
    ),
    (EntityType.character, ContentCategory.backstory): (
        "period clothing, clothing style, clothing colors, materials, physical setting, social status, "
        "items carried, physical state, visible symbols, location elements mentioned"
    ),
    (EntityType.character, ContentCategory.scene): (
        "posture, clothing, accessories, equipment, items carried, visible expression, "
        "lighting on character, surrounding environment mentioned, action performed, position in space"
    ),
    (EntityType.character, ContentCategory.chapter): (
        "position in space, clothing, accessories, visible expression, lighting, atmosphere, "
        "surrounding environment mentioned"
    ),
    (EntityType.creature, ContentCategory.extended_description): (
        "species, body type, colors (all mentioned), textures (skin/fur/scales), "
        "distinctive features (wings, tail, horns, claws, tentacles, eyes, mouth), size, posture, "
        "fantastical elements (magic, energy, luminescence, aura), marks, scars, associated natural elements"
    ),
    (EntityType.creature, ContentCategory.backstory): (
        "native environment, physical condition, colors from that era, distinctive features from youth, "
        "atmosphere of the place, surrounding environment mentioned"
    ),
    (EntityType.creature, ContentCategory.scene): (
        "position, action, visible body language, interaction with environment, "
        "lighting, surrounding environment mentioned"
    ),
    (EntityType.creature, ContentCategory.chapter): (
        "position, action, environment, lighting, atmosphere, surrounding environment mentioned"
    ),
    (EntityType.location, ContentCategory.extended_description): (
        "environment type, architectural style, materials (all), colors mentioned, distinctive elements, "
        "typical lighting, scale, atmosphere, natural elements, furniture, decoration, visible symbols"
    ),
    (EntityType.location, ContentCategory.backstory): (
        "original appearance, period architectural style, construction materials, colors, "
        "current vs past state, distinctive symbols, elements that changed, elements that remain"
    ),
    (EntityType.location, ContentCategory.scene): (
        "foreground elements, lighting, climate, atmosphere, action occurring, "
        "surrounding environment, colors mentioned, textures"
    ),
    (EntityType.location, ContentCategory.chapter): (
        "space description, architectural style, materials, lighting, atmosphere, "
        "elements present, colors, textures"
    ),
    (EntityType.faction, ContentCategory.extended_description): (
        "emblem/heraldry style, main symbol, secondary symbols, color palette (all), "
        "material appearance, mood, associated architectural elements, writing/symbols type, "
        "insignias, uniforms, decoration, band colors"
    ),
    (EntityType.faction, ContentCategory.backstory): (
        "period style, original symbols, founding colors, visible power elements, "
        "historical emblems, period clothing, associated architecture"
    ),
    (EntityType.faction, ContentCategory.scene): (
        "visible symbol, dominant colors, member presence, uniforms, insignia, "
        "visible weapons, atmosphere, member expressions"
    ),
    (EntityType.faction, ContentCategory.chapter): (
        "visible symbol, colors, presence, atmosphere, visible uniforms"
    ),
    (EntityType.item, ContentCategory.extended_description): (
        "object type, main material, secondary materials, colors (all), texture, condition, size, "
        "decorative elements, indicators (glow, runes, energy, magic), engraved symbols, marks, "
        "included accessories, visible parts"
    ),
    (EntityType.item, ContentCategory.backstory): (
        "original appearance, period materials, original colors, visible engraved symbols, "
        "condition at that time, period decorative elements, frames, mounts"
    ),
    (EntityType.item, ContentCategory.scene): (
        "how displayed, position, lighting, character interaction, visible state, glow, visible damage"
    ),
    (EntityType.item, ContentCategory.chapter): (
        "presence, position, lighting, visible state, colors"
    ),
}
"""Atributos visuales esperados por combinación de tipo de entidad y categoría."""


def build_combined_prompt(
    entity_type: EntityType,
    category: ContentCategory,
    content_text: str,
) -> str:
    """Construye el prompt para extraer tipo y atributos visuales en una sola llamada LLM.

    La salida esperada del LLM es una lista comma-separated con el tipo como primer
    elemento, directamente usable como prompt positivo para modelos de imagen.
    Ejemplo de salida: human, tall, dark hooded cloak, silver eyes, weathered skin
    """
    type_options = _COMBINED_TYPE_OPTIONS.get(entity_type, entity_type.value)
    entity_en = _ENTITY_NAME_EN.get(entity_type, entity_type.value)
    attrs = _ATTRIBUTOS_BY_ENTITY_CATEGORY.get(
        (entity_type, category),
        "colors, shapes, textures, sizes",
    )
    ignore = _IGNORA_BY_CATEGORY.get(category, "IGNORE: narrative, history.")
    backstory_hint = (
        "IMPORTANT: The very first item MUST be a type from the list above, even in historical or backstory text.\n"
        if category == ContentCategory.backstory
        else ""
    )

    return (
        f"From the following text, extract the specific type of {entity_en} and ALL visual attributes mentioned.\n"
        f"Output as a single comma-separated list: start with the specific type ({type_options}),\n"
        f"then ALL visual details — {attrs}.\n"
        f"{ignore}\n"
        f"{backstory_hint}"
        f"ENGLISH ONLY. No explanation, no sentences, no extra lines.\n"
        f"Example: human, tall, dark hooded cloak, silver eyes, weathered skin\n\n"
        f"TEXT:\n---\n{content_text}\n---"
    )
