from langgraph.graph import StateGraph, START, add_messages
from langgraph.types import Command, interrupt
from typing import TypedDict, Annotated, List
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import init_chat_model
import os

load_dotenv()

def create_llm():
    provider = os.getenv("LLM_PROVIDER", "google_genai")
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    return init_chat_model(
        model=model,
        model_provider=provider,
        temperature=temperature
    )

llm = create_llm()

class State(TypedDict): 
    topic: str
    content_length: str
    writing_style: str
    generated_post: Annotated[List[str], add_messages]
    human_feedback: Annotated[List[str], add_messages]
    should_continue: bool

def content_generator(state: State): 
    """Generate content based on user ideas and incorporate human feedback"""

    print("[content_generator] Generating content")
    topic = state["topic"]
    content_length = state.get("content_length", "medium")
    writing_style = state.get("writing_style", "")
    feedback = state["human_feedback"] if "human_feedback" in state else ["No Feedback yet"]

    # Here, we define the prompt 
    style_instruction = f"Writing Style: {writing_style}" if writing_style.strip() else ""

    prompt = f"""

        Content Ideas & Details: {topic}
        Content Length: {content_length}
        {style_instruction}
        Human Feedback: {feedback[-1] if feedback else "No feedback yet"}

        The user has provided their content ideas and details above. Your task is to expand on these ideas and create a structured, engaging content post. 
        
        Instructions:
        - Take the user's ideas, points, and details as your foundation
        - Expand and develop their concepts into a well-structured post
        - Maintain their intended message while enhancing clarity and engagement
        - If they provided specific points, examples, or experiences, incorporate and elaborate on them
        - Create compelling hooks, smooth transitions, and strong conclusions
        - Ensure the content matches the desired length and writing style
        {" Follow the specified writing style carefully." if writing_style.strip() else ""}

        Consider previous human feedback to refine the response and make improvements.
    """

    response = llm.invoke([
        SystemMessage(content="You are an expert content writer who specializes in expanding user ideas into engaging, well-structured content. You excel at taking initial concepts, details, and rough ideas and transforming them into polished, professional content while preserving the user's original intent and voice. You work collaboratively with human feedback to continuously improve the content."), 
        HumanMessage(content=prompt)
    ])

    generated_content_post = response.content

    print(f"[content_generator] Generated post:\n{generated_content_post}\n")

    return {
       "generated_post": [AIMessage(content=generated_content_post)] , 
       "human_feedback": feedback
    }

def feedback_collector(state: State): 
    """Collect human feedback and decide next action"""

    print("\n [feedback_collector] awaiting human feedback...")

    generated_post = state["generated_post"]

    # Interrupt to get user feedback
    user_feedback = interrupt(
        {
            "generated_post": generated_post, 
            "message": "Provide feedback or type 'done' to finish"
        }
    )

    print(f"[feedback_collector] Received human feedback: {user_feedback}")

    # Update feedback and set decision flag
    updated_feedback = state["human_feedback"] + [user_feedback]
    
    return {
        "human_feedback": updated_feedback,
        "should_continue": user_feedback.lower() != "done"
    }


def content_finalizer(state: State): 
    """Finalize the content generation process"""
    print("\n[content_finalizer] Content finalized")
    return {"generated_post": state["generated_post"], "human_feedback": state["human_feedback"]}

def should_continue_feedback(state: State) -> str:
    """Route based on whether user wants to continue providing feedback"""
    if state.get("should_continue", True):
        return "content_generator"
    else:
        return "content_finalizer"


# Build the conversation graph
graph = StateGraph(State)
graph.add_node("content_generator", content_generator)
graph.add_node("feedback_collector", feedback_collector)
graph.add_node("content_finalizer", content_finalizer)

# Define the flow with explicit feedback loop
graph.add_edge(START, "content_generator")
graph.add_edge("content_generator", "feedback_collector")

# Add conditional edge for the feedback loop
graph.add_conditional_edges(
    "feedback_collector",
    should_continue_feedback,
    {
        "content_generator": "content_generator",  # Loop back for more iterations
        "content_finalizer": "content_finalizer"   # Finalize when done
    }
)

graph.set_finish_point("content_finalizer")

# Enable Interrupt mechanism
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

# For standalone testing only
if __name__ == "__main__":
    import uuid
    
    thread_config = {"configurable": {
        "thread_id": uuid.uuid4()
    }}

    topic = input("Enter your content ideas: ")
    initial_state = {
        "topic": topic, 
        "generated_post": [], 
        "human_feedback": [],
        "should_continue": True
    }

    try:
        for chunk in app.stream(initial_state, config=thread_config):
            for node_id, value in chunk.items():
                if node_id == "__interrupt__":
                    while True: 
                        user_feedback = input("Provide feedback (or type 'done' when finished): ")
                        app.invoke(Command(resume=user_feedback), config=thread_config)
                        if user_feedback.lower() == "done":
                            break
    except Exception as e:
        print(f"An error occurred: {e}")