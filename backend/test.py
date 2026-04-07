from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from config import settings

template = """Question: {question}

Answer: Let's think step by step."""

prompt = ChatPromptTemplate.from_template(template)

model = OllamaLLM(
    model=settings.ollama_model
)

chain = prompt | model

# chain.invoke({"question": "What is LangChain?"})

print(chain.invoke({"question": "What is LangChain?"}))