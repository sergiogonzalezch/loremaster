# Domain rules para extracción de atributos visuales para generación de imágenes
# Estas instrucciones guían al LLM para extraer atributos visuales del texto
# Sin resumir, omitir o filtrar - solo extraer lo que el texto menciona

from app.models.enums import ContentCategory
from app.models.entities import EntityType

# === CONSTANTES REUTILIZABLES ===

_BASE_EXTRACT = "extrae TODOS los atributos visuales que el texto EXPLÍCITAMENTE menciona. "
_NO_SKIP = "NO resumas, NO omitas. Cada detalle visual debe incluirse. "
_FORMAT_ATTRS = "SOLO atributos sueltos, NO frases completas. "

_IGNORA_BY_CATEGORY = {
    ContentCategory.extended_description: "IGNORA: narrativa, motivaciones, historia, nombres.",
    ContentCategory.backstory: "IGNORA: nombres, fechas, eventos históricos, motivaciones.",
    ContentCategory.scene: "IGNORA: diálogo, pensamientos, emociones.",
    ContentCategory.chapter: "IGNORA: trama, desarrollo, personajes secundarios.",
}

_ENTITY_NAME_ES = {
    EntityType.character: "personaje",
    EntityType.creature: "criatura",
    EntityType.location: "lugar",
    EntityType.faction: "facción",
    EntityType.item: "objeto",
}

_TYPE_LABEL_BY_ENTITY = {
    EntityType.character: "Incluye el TIPO de entidad: robot, androide, cyborg, humano, alien, demonio, ángel, bestia, criatura mítica.",
    EntityType.creature: "Incluye el TIPO de criatura: dragón, bestia, espíritu, demonio, ángel, ser mitológico, monstruo, animal, insecto, planta.",
    EntityType.location: "Incluye el TIPO de lugar: ciudad, fortaleza, templo, bosque, montaña, ruina, nave, planeta, dimensión.",
    EntityType.faction: "Incluye el TIPO de facción: reino, clan, hermandad, orden, guild, corporation, religión, movimiento.",
    EntityType.item: "Incluye el TIPO de objeto: arma, armadura, herramienta, relicto, artefacto, joyería, instrumento, vehículo.",
}

_TYPE_EXTRACT_PROMPT = {
    EntityType.character: (
        "Del siguiente texto, identifica el tipo específico de ser que describe. "
        "Solo responde con una palabra o término corto: robot, androide, cyborg, humano, alien, "
        "demonio, ángel, bestia, criatura mítica, u otro que aparezca explícitamente. "
        "Si no hay un tipo específico claro, responde 'personaje'."
    ),
    EntityType.creature: (
        "Del siguiente texto, identifica el tipo específico de criatura. "
        "Solo responde con una palabra o término corto: dragón, bestia, espíritu, demonio, ángel, "
        "ser mitológico, monstruo, animal, insecto, planta, u otro que aparezca explícitamente. "
        "Si no hay un tipo específico claro, responde 'criatura'."
    ),
    EntityType.location: (
        "Del siguiente texto, identifica el tipo específico de lugar. "
        "Solo responde con una palabra o término corto: ciudad, fortaleza, templo, bosque, montaña, "
        "ruina, nave, planeta, dimensión, villa, aldea, prisión, biblioteca, u otro que aparezca explícitamente. "
        "Si no hay un tipo específico claro, responde 'lugar'."
    ),
    EntityType.faction: (
        "Del siguiente texto, identifica el tipo específico de facción. "
        "Solo responde con una palabra o término corto: reino, clan, hermandad, orden, guild, "
        "corporation, religión, movimiento, ejército, culto, u otro que aparezca explícitamente. "
        "Si no hay un tipo específico claro, responde 'facción'."
    ),
    EntityType.item: (
        "Del siguiente texto, identifica el tipo específico de objeto. "
        "Solo responde con una palabra o término corto: espada, arco, varita, escudo, armadura, "
        "relicto, artefacto, joyería, amuleto, poción, libro, instrumento, vehículo, u otro que aparezca explícitamente. "
        "Si no hay un tipo específico claro, responde 'objeto'."
    ),
}

_ATRIBUTOS_BY_ENTITY_CATEGORY = {
    (EntityType.character, ContentCategory.extended_description): (
        "colores, materiales, formas del cuerpo, texturas, tamaños, vestimenta, accesorios, equipamiento, "
        "marcas, detalles distintivos, expresiones faciales, postura, condiciones físicas, elementos que porta, "
        "elementos del entorno mencionados"
    ),
    (EntityType.character, ContentCategory.backstory): (
        "ropa de época, estilo de ropa, colores de vestimenta, materiales, entorno físico, condición social, "
        "objetos que porta, estado físico, símbolos visibles, elementos del lugar mencionados"
    ),
    (EntityType.character, ContentCategory.scene): (
        "postura, vestimenta, accesorios, equipamiento, objetos que porta, expresión visible, "
        "iluminación sobre el personaje, elementos del entorno mencionados, acción que realiza, posición en el espacio"
    ),
    (EntityType.character, ContentCategory.chapter): (
        "posición en el espacio, vestimenta, accesorios, expresión visible, iluminación, atmósfera, "
        "elementos del entorno mencionados"
    ),
    (EntityType.creature, ContentCategory.extended_description): (
        "especie, tipo de cuerpo, colores (todos los mencionados), texturas (piel/pelaje/escamas), "
        "características distintivas (alas, cola, cuernos, garras, tentáculos, ojos, boca), tamaño, postura, "
        "elementos fantásticos (magia, energía, luminescencia, aura), marcas, cicatrices, elementos naturales asociados"
    ),
    (EntityType.creature, ContentCategory.backstory): (
        "entorno nativo, condición física, colores de esa época, características distintivas que tuvo desde joven, "
        "atmósfera del lugar, elementos del entorno mencionados"
    ),
    (EntityType.creature, ContentCategory.scene): (
        "posición, acción, expresión corporal visible, interacción con entorno, iluminación, elementos del entorno mencionados"
    ),
    (EntityType.creature, ContentCategory.chapter): (
        "posición, acción, entorno, iluminación, atmósfera, elementos del entorno mencionados"
    ),
    (EntityType.location, ContentCategory.extended_description): (
        "tipo de entorno, estilo arquitectónico, materiales (todos), colores mencionados, elementos distintivos, "
        "iluminación típica, escala, atmósfera, elementos naturales, muebles, decoración, símbolos visibles"
    ),
    (EntityType.location, ContentCategory.backstory): (
        "apariencia original, estilo arquitectónico de época, materiales de construcción, colores, "
        "estado actual vs pasado, símbolos distintivos, elementos que han cambiado, elementos que permanecen"
    ),
    (EntityType.location, ContentCategory.scene): (
        "elementos en primer plano, iluminación, clima, atmósfera, acción que ocurre, elementos del entorno, "
        "colores mencionados, texturas"
    ),
    (EntityType.location, ContentCategory.chapter): (
        "descripción del espacio, estilo arquitectónico, materiales, iluminación, atmósfera, elementos presentes, colores, texturas"
    ),
    (EntityType.faction, ContentCategory.extended_description): (
        "estilo del emblema/heraldry, símbolo principal, símbolos secundarios, paleta de colores (todos), "
        "material appearance, mood, elementos arquitectónicos asociados, tipo de escritura/símbolos, "
        "insignias, uniformes, decoración, colores de banda"
    ),
    (EntityType.faction, ContentCategory.backstory): (
        "estilo de la época, símbolos originales, colores fundacionales, elementos de poder visibles, "
        "emblemas históricos, vestimenta de época, arquitectura asociada"
    ),
    (EntityType.faction, ContentCategory.scene): (
        "símbolo visible, colores dominantes, presencia de miembros, uniformes, insignias, armamento visible, "
        "atmósfera, expresión de integrantes"
    ),
    (EntityType.faction, ContentCategory.chapter): (
        "símbolo visible, colores, presencia, atmósfera, uniformes visibles"
    ),
    (EntityType.item, ContentCategory.extended_description): (
        "tipo de objeto, material principal, materiales secundarios, colores (todos), textura, condición, tamaño, "
        "elementos decorativos, indicadores (brillo, runas, energía, magia), símbolos grabados, marcas, "
        "accesorios incluidos, partes visibles"
    ),
    (EntityType.item, ContentCategory.backstory): (
        "apariencia original, materiales de la época, colores originales, símbolos grabados visibles, "
        "condición en ese tiempo, elementos decorativos de época, marcos, monturas"
    ),
    (EntityType.item, ContentCategory.scene): (
        "cómo se muestra, posición, iluminación, interacción con personajes, estado visible, brillo, daños visibles"
    ),
    (EntityType.item, ContentCategory.chapter): (
        "presencia, posición, iluminación, estado visible, colores"
    ),
}

_PREFIX_BY_CATEGORY = {
    ContentCategory.extended_description: "Del siguiente texto que describe",
    ContentCategory.backstory: "Del siguiente texto de trasfondo de",
    ContentCategory.scene: "De la siguiente escena",
    ContentCategory.chapter: "Del siguiente capítulo, extrae los atributos visuales en la escena de apertura de",
}


# === BUILDER FUNCTIONS ===

def _build_instruction(entity_type: EntityType, category: ContentCategory) -> str:
    """Construye la instrucción LLM para una combinación entity_type + category."""
    prefix = _PREFIX_BY_CATEGORY.get(category, "Del siguiente texto")
    entity_es = _ENTITY_NAME_ES.get(entity_type, entity_type.value)
    if category == ContentCategory.chapter:
        entity_desc = f"{entity_es} que el texto menciona"
    else:
        entity_desc = f"un {entity_es}"

    attrs = _ATRIBUTOS_BY_ENTITY_CATEGORY.get((entity_type, category), "colores, formas, texturas, tamaños")
    type_label = _TYPE_LABEL_BY_ENTITY.get(entity_type, "")
    ignore = _IGNORA_BY_CATEGORY.get(category, "IGNORA: narrativa, historia.")

    return (
        f"{prefix} {entity_desc}, {_BASE_EXTRACT}"
        f"{_NO_SKIP}"
        f"{_FORMAT_ATTRS}"
        f"Incluye TODOS: {attrs}. "
        f"{type_label} "
        f"Formato: lista de atributos separados por coma. "
        f"{ignore}"
    )


# === BUILD DICTIONARY ===

_llm_instruction_by_entity_category = {
    (entity_type, category): _build_instruction(entity_type, category)
    for entity_type in EntityType
    for category in ContentCategory
    if (entity_type, category) in _ATRIBUTOS_BY_ENTITY_CATEGORY
}