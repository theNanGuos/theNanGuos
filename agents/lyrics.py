from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import lyrics

class LyricsAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "Lyrics Agent",
            llm = llm,
            system_prompt = (
                lyrics()
            )
        )