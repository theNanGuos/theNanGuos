# src/multi_agent_demo/graph.py

from langgraph.graph import END, START, StateGraph

from agents.base import Agent
from agents.conductor import ConductorAgent
from agents.lyrics import LyricsAgent
from agents.melody import MelodyAgent
from agents.arrange import ArrangeAgent
from models.state import State


def route_from_start(state: State) -> str:
    return "conductor"


def build_graph(llm):
    builder = StateGraph(State)

    conductor = ConductorAgent(llm)
    lyrics = LyricsAgent(llm)
    melody = MelodyAgent(llm)
    arrange = ArrangeAgent(llm)

    builder.add_node("conductor", conductor)
    builder.add_node("lyrics", lyrics)
    builder.add_node("melody", melody)
    builder.add_node("arrange", arrange)

    builder.add_conditional_edges(
        START,
        route_from_start,
        {
            "conductor": "conductor",
        },
    )

    builder.add_edge("conductor", "melody")
    builder.add_edge("melody", "lyrics")
    builder.add_edge("lyrics", "arrange")
    builder.add_edge("arrange", END)

    return builder.compile()