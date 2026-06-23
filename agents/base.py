from abc import ABC
from dataclasses import dataclass
from langchain_core.messages import SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from models.state import State

@dataclass
class Agent(ABC):
    name: str
    system_prompt: str
    llm: BaseChatModel

    def __call__(self, state: State) -> dict:
        messages = [
            SystemMessage(content=self.system_prompt),
            *state["messages"],
        ]
        response = self.llm.invoke(messages)
        return {
            "messages": [response]
        }
