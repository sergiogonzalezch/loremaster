from app.models.enums import ContentCategory

_SAFETY_INSTRUCTION = (
    "RESTRICCIONES ABSOLUTAS: Bajo ninguna circunstancia generes contenido que incluya "
    "material sexual explícito, instrucciones para actividades ilegales o dañinas, "
    "discurso de odio, acoso o contenido denigrante hacia personas o grupos. "
    "Si la solicitud o el contexto contienen ese tipo de material, responde únicamente: "
    "'No puedo procesar esta solicitud.' y no generes ningún contenido adicional. "
)
_PREAMBLE = "Eres un escritor experto en narrativa y worldbuilding. "
_ONLY_CONTEXT = "Usa ÚNICAMENTE la información del contexto proporcionado."
_SECTIONS = "\n\nCONTEXTO:\n{context}\n\nSOLICITUD:\n{query}"

_TEMPLATES: dict[ContentCategory, str] = {
    ContentCategory.backstory: (
        _SAFETY_INSTRUCTION
        + _PREAMBLE
        + "Genera una historia de fondo para '{entity_name}' ({entity_type}). "
        + "Incluye orígenes, motivaciones y eventos formativos. "
        + _ONLY_CONTEXT
        + " Si el contexto no es suficiente, indícalo."
        + _SECTIONS
    ),
    ContentCategory.extended_description: (
        _SAFETY_INSTRUCTION
        + _PREAMBLE
        + "Expande la descripción de '{entity_name}' ({entity_type}). "
        + "Detalla rasgos, apariencia, personalidad o características distintivas "
        + "sin inventar eventos narrativos. "
        + _ONLY_CONTEXT
        + _SECTIONS
    ),
    ContentCategory.scene: (
        _SAFETY_INSTRUCTION
        + _PREAMBLE
        + "Narra una escena que involucre a '{entity_name}' ({entity_type}). "
        + "Incluye ambientación, diálogo y acción. "
        + _ONLY_CONTEXT
        + _SECTIONS
    ),
    ContentCategory.chapter: (
        _SAFETY_INSTRUCTION
        + _PREAMBLE
        + "Escribe un capítulo narrativo centrado en '{entity_name}' ({entity_type}). "
        + "Estructura con inicio, desarrollo y cierre. "
        + _ONLY_CONTEXT
        + _SECTIONS
    ),
}


def get_template(category: ContentCategory) -> str:
    return _TEMPLATES[category]


def render_prompt(
    category: ContentCategory,
    entity_name: str,
    entity_type: str,
    context: str,
    query: str,
) -> str:
    def _escape(v: str) -> str:
        return v.replace("{", "{{").replace("}", "}}")

    return get_template(category).format(
        entity_name=_escape(entity_name),
        entity_type=_escape(entity_type),
        context=_escape(context),
        query=_escape(query),
    )
