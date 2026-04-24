from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings

_PROMPT = PromptTemplate.from_template("""
    Eres un asistente experto en narrativa y worldbuilding.\n
    Responde usando ÚNICAMENTE la información del contexto proporcionado.\n
    Si el contexto no contiene información suficiente, indícalo claramente.\n\n
    CONTEXTO:\n{context},\n
    PREGUNTA:\n{query}.
    """)

llm = OllamaLLM(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=settings.temperature,
    num_predict=settings.max_tokens,
)

chain = _PROMPT | llm | StrOutputParser()
