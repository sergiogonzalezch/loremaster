from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
    temperature=float(os.getenv("TEMPERATURE", "0.7")),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", None)
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Eres un asistente útil. Responde de forma breve."),
    ("human", "{question}")
])

chain = prompt | llm | StrOutputParser()

response = chain.invoke({"question": "¿Qué es Python en una oración?"})
print(response)