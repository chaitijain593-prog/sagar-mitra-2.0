from typing import TypedDict, List
from langgraph.graph import StateGraph, END

# Import your real worker nodes
from app.sub_agents import navigation_node, fishing_node, compliance_node

# Import the Gemini advisory formatter to keep your persona and language features
from app.advisory import plain_gemini_answer

# 1. Define the shared state dictionary (The backpack that passes data between agents)
class AgentState(TypedDict):
    user_message: str
    coordinates: List[float]  # e.g., [18.9, 72.8] for Mumbai
    next_step: str
    hazard_alerts: List[str]
    final_output: str
    final_advisory: str

def create_orca_graph():
    workflow = StateGraph(AgentState)

    # 2. The Supervisor / Router Node (Decides who handles the task)
    def supervisor_node(state: AgentState):
        print("--- SUPERVISOR: Routing user request ---")
        query = state.get("user_message", "").lower()
        
        if "wave" in query or "safe" in query or "weather" in query:
            state["next_step"] = "navigation"
        elif "fish" in query or "catch" in query or "pfz" in query:
            state["next_step"] = "fishing"
        else:
            state["next_step"] = "compliance"
            
        return state

    # 3. Synthesizer Node (Combines all reports at the end and formats via Gemini)
    def synthesizer_node(state: AgentState):
        print("--- SYNTHESIZER: Formatting final report via Gemini ---")
        raw_output = state.get("final_output", "Standard maritime check complete.")
        
        try:
            # Use the existing Gemini logic to format the agent's raw output
            prompt = f"Translate this raw agent data into a clear advisory for the user: {raw_output}"
            polished_advisory = plain_gemini_answer(
                user_message=prompt, 
                persona="Fisherman", 
                language="English" 
            )
            state["final_advisory"] = polished_advisory
        except Exception as e:
            print(f"[Synthesizer Error] Falling back to raw output: {e}")
            # Fallback just in case Gemini API quota is hit or internet drops during the demo
            state["final_advisory"] = f"ORCA Official Advisory: {raw_output}"
            
        return state

    # Register all nodes into the graph
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("navigation", navigation_node)
    workflow.add_node("fishing", fishing_node)
    workflow.add_node("compliance", compliance_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Define entry point and conditional routing
    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next_step"],
        {
            "navigation": "navigation",
            "fishing": "fishing",
            "compliance": "compliance"
        }
    )

    # Connect all workers to the synthesizer, then end
    workflow.add_edge("navigation", "synthesizer")
    workflow.add_edge("fishing", "synthesizer")
    workflow.add_edge("compliance", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()