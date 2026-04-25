from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings

_SAFETY_INSTRUCTION = (
    "RESTRICCIONES ABSOLUTAS: Bajo ninguna circunstancia generes contenido que incluya "
    "material sexual explícito, instrucciones para actividades ilegales o dañinas, "
    "discurso de odio, acoso o contenido denigrante hacia personas o grupos. "
    "Si la solicitud o el contexto contienen ese tipo de material, responde únicamente: "
    "'No puedo procesar esta solicitud.' y no generes ningún contenido adicional.\n\n"
)

_PROMPT = PromptTemplate.from_template(
    """
    """
    + _SAFETY_INSTRUCTION
    + """
    Eres un asistente experto en narrativa y worldbuilding.\n
    Responde usando ÚNICAMENTE la información del contexto proporcionado.\n
    Si el contexto no contiene información suficiente, indícalo claramente.\n\n
    CONTEXTO:\n{context},\n
    PREGUNTA:\n{query}.
    """
)

llm = OllamaLLM(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=settings.temperature,
    num_predict=settings.max_tokens,
)

chain = _PROMPT | llm | StrOutputParser()
