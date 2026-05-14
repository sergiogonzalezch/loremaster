"""Configuración del modelo LLM (Ollama) y cadena de procesamiento para RAG."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from app.core.config import settings

_SAFETY_INSTRUCTION = (
    "No generes contenido sexual explícito, instrucciones dañinas ni discurso de odio. "
    "Si la solicitud lo requiere, responde únicamente: 'No puedo procesar esta solicitud.'\n\n"
)
"""Instrucción de seguridad reducida para el pipeline RAG libre (consultas de colección).
La instrucción completa vive en prompt_templates.py para el pipeline de generación de entidades."""

_PROMPT = PromptTemplate.from_template(
    _SAFETY_INSTRUCTION
    + "Eres un asistente experto en narrativa y worldbuilding.\n"
    + "Usa la información del contexto para responder. "
    + "Si el contexto es insuficiente, genera con lo disponible "
    + "y añade al final una nota breve indicando qué información adicional enriquecería la respuesta.\n"
    + "Extensión: 2-3 párrafos.\n\n"
    + "<context>\n{context}\n</context>\n\n"
    + "<question>\n{query}\n</question>"
)
"""Plantilla de prompt para consultas RAG."""

llm = OllamaLLM(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=settings.temperature,
    num_predict=settings.max_tokens,
)
"""Instancia del modelo Ollama configurada con los parámetros de la aplicación."""

chain = _PROMPT | llm | StrOutputParser()
"""Cadena de procesamiento LangChain: prompt → LLM → parser de salida."""
