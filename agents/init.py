import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def create_llm() -> ChatOpenAI:
    load_dotenv()

    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "glm-5.1"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )