# Domain rules for visual attribute extraction for image generation
# These instructions guide the LLM to extract visual attributes from text
# Without summarizing, skipping, or filtering - only extract what the text mentions

from app.models.enums import ContentCategory
from app.models.entities import EntityType

# === REUSABLE CONSTANTS ===

ENGLISH_RESPONSE_INSTRUCTION = "Respond IN ENGLISH"
_TYPE_EXTRACT_SUFFIX = f". {ENGLISH_RESPONSE_INSTRUCTION} with only one word or short term: "

_BASE_EXTRACT = "extract ALL visual attributes that the text EXPLICITLY mentions. "
_NO_SKIP = "DO NOT summarize, DO NOT skip. Every visual detail must be included. "
_FORMAT_ATTRS = f"ONLY loose attributes in ENGLISH, NO complete sentences. {ENGLISH_RESPONSE_INSTRUCTION}. "

_IGNORA_BY_CATEGORY = {
    ContentCategory.extended_description: "IGNORE: narrative, motivations, history, names.",
    ContentCategory.backstory: "IGNORE: names, dates, historical events, motivations.",
    ContentCategory.scene: "IGNORE: dialogue, thoughts, emotions.",
    ContentCategory.chapter: "IGNORE: plot, development, secondary characters.",
}

_ENTITY_NAME_EN = {
    EntityType.character: "character",
    EntityType.creature: "creature",
    EntityType.location: "location",
    EntityType.faction: "faction",
    EntityType.item: "item",
}

_TYPE_LABEL_BY_ENTITY = {
    EntityType.character: "Include the ENTITY TYPE: robot, android, cyborg, human, alien, demon, angel, beast, mythical creature.",
    EntityType.creature: "Include the CREATURE TYPE: dragon, beast, spirit, demon, angel, mythological being, monster, animal, insect, plant.",
    EntityType.location: "Include the LOCATION TYPE: city, fortress, temple, forest, mountain, ruin, ship, planet, dimension.",
    EntityType.faction: "Include the FACTION TYPE: kingdom, clan, brotherhood, order, guild, corporation, religion, movement.",
    EntityType.item: "Include the OBJECT TYPE: weapon, armor, tool, relic, artifact, jewelry, instrument, vehicle.",
}

_TYPE_EXTRACT_PROMPT = {
    EntityType.character: (
        f"From the following text, identify the specific type of being described. "
        f"{_TYPE_EXTRACT_SUFFIX}robot, android, cyborg, human, alien, "
        "demon, angel, beast, mythical creature, or other that appears explicitly. "
        "If no specific type is clear, respond 'character'."
    ),
    EntityType.creature: (
        f"From the following text, identify the specific type of creature. "
        f"{_TYPE_EXTRACT_SUFFIX}dragon, beast, spirit, demon, angel, "
        "mythological being, monster, animal, insect, plant, or other that appears explicitly. "
        "If no specific type is clear, respond 'creature'."
    ),
    EntityType.location: (
        f"From the following text, identify the specific type of location. "
        f"{_TYPE_EXTRACT_SUFFIX}city, fortress, temple, forest, mountain, "
        "ruin, ship, planet, dimension, village, town, prison, library, or other that appears explicitly. "
        "If no specific type is clear, respond 'location'."
    ),
    EntityType.faction: (
        f"From the following text, identify the specific type of faction. "
        f"{_TYPE_EXTRACT_SUFFIX}kingdom, clan, brotherhood, order, guild, "
        "corporation, religion, movement, army, cult, or other that appears explicitly. "
        "If no specific type is clear, respond 'faction'."
    ),
    EntityType.item: (
        f"From the following text, identify the specific type of object. "
        f"{_TYPE_EXTRACT_SUFFIX}sword, bow, wand, shield, armor, "
        "relic, artifact, jewelry, amulet, potion, book, instrument, vehicle, or other that appears explicitly. "
        "If no specific type is clear, respond 'item'."
    ),
}

_ATTRIBUTOS_BY_ENTITY_CATEGORY = {
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
        "position, action, visible body language, interaction with environment, lighting, surrounding environment mentioned"
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
        "foreground elements, lighting, climate, atmosphere, action occurring, surrounding environment, "
        "colors mentioned, textures"
    ),
    (EntityType.location, ContentCategory.chapter): (
        "space description, architectural style, materials, lighting, atmosphere, elements present, colors, textures"
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
        "visible symbol, dominant colors, member presence, uniforms, insignia, visible weapons, "
        "atmosphere, member expressions"
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

_PREFIX_BY_CATEGORY = {
    ContentCategory.extended_description: "From the following text describing",
    ContentCategory.backstory: "From the following backstory text of",
    ContentCategory.scene: "From the following scene",
    ContentCategory.chapter: "From the following chapter, extract visual attributes in the opening scene of",
}


# === BUILDER FUNCTIONS ===

def _build_instruction(entity_type: EntityType, category: ContentCategory) -> str:
    """Builds the LLM instruction for an entity_type + category combination."""
    prefix = _PREFIX_BY_CATEGORY.get(category, "From the following text")
    entity_en = _ENTITY_NAME_EN.get(entity_type, entity_type.value)
    if category == ContentCategory.chapter:
        entity_desc = f"{entity_en} that the text mentions"
    else:
        entity_desc = f"a {entity_en}"

    attrs = _ATTRIBUTOS_BY_ENTITY_CATEGORY.get((entity_type, category), "colors, shapes, textures, sizes")
    type_label = _TYPE_LABEL_BY_ENTITY.get(entity_type, "")
    ignore = _IGNORA_BY_CATEGORY.get(category, "IGNORE: narrative, history.")

    return (
        f"{prefix} {entity_desc}, {_BASE_EXTRACT}"
        f"{_NO_SKIP}"
        f"{_FORMAT_ATTRS}"
        f"Include ALL: {attrs}. "
        f"{type_label} "
        f"Format: list of attributes separated by comma. "
        f"{ignore}"
    )


# === BUILD DICTIONARY ===

_llm_instruction_by_entity_category = {
    (entity_type, category): _build_instruction(entity_type, category)
    for entity_type in EntityType
    for category in ContentCategory
    if (entity_type, category) in _ATTRIBUTOS_BY_ENTITY_CATEGORY
}