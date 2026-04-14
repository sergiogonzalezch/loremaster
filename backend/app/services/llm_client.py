from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import settings

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un asistente experto en narrativa y worldbuilding.\n"
            "Responde usando ÚNICAMENTE la información del contexto proporcionado.\n"
            "Si el contexto no contiene información suficiente, indícalo claramente.\n\n"
            "CONTEXTO:\n{context}",
        ),
        ("human", "{query}"),
    ]
)


def _get_llm():
    llm_instance = OllamaLLM(
        model=settings.ollama_model,
        temperature=settings.temperature,
        num_predict=settings.max_tokens,
    )
    return llm_instance


def get_chain():
    return _PROMPT | _get_llm() | StrOutputParser()
