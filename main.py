from langchain_core.messages import HumanMessage

from agents.init import create_llm
from app.graph import build_graph
from lib.suno import generate

def main() -> None:
    llm = create_llm()
    graph = build_graph(llm)

    user_input = "生成一首钢琴协奏曲，风格恢弘壮阔，长度在三分钟左右"

    result = graph.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
        }
    )
    print(f"prompt: {result["messages"][-1].content}")
    generate(result["messages"][-1].content)



if __name__ == "__main__":
    main()