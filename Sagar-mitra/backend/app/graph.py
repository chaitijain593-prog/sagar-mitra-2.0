from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

# 1. Define the shared state dictionary (The backpack that passes data between agents)
class AgentState(TypedDict):
    user_message: str
    coordinates: List[float]  # e.g., [18.9, 72.8] for Mumbai
    next_step: str
    navigation_result: Dict[str, Any]
    fishing_result: Dict[str, Any]
    compliance_result: Dict[str, Any]
    final_advisory: str

def create_orca_graph():
    workflow = StateGraph(AgentState)

    # 2. The Supervisor / Router Node (Decides who handles the task)
    def supervisor_node(state: AgentState):
        print("--- SUPERVISOR: Routing user request ---")
        query = state.get("user_message", "").lower()
        
        if "wave" in query or "safe" in query:
            state["next_step"] = "navigation"
        elif "fish" in query or "catch" in query:
            state["next_step"] = "fishing"
        else:
            state["next_step"] = "compliance"
            
        return state

    # Worker nodes
    def navigation_node(state: AgentState):
        state["navigation_result"] = {"status": "SAFE", "waves": "1.2m"}
        return state

    def fishing_node(state: AgentState):
        state["fishing_result"] = {"zone": "PFZ Active", "port": "Ratnagiri"}
        return state

    def compliance_node(state: AgentState):
        state["compliance_result"] = {"boundary": "Inside Indian EEZ"}
        return state

    # Synthesizer Node (Combines all reports at the end)
    def synthesizer_node(state: AgentState):
        print("--- SYNTHESIZER: Merging reports ---")
        state["final_advisory"] = "Advisory: Vessel is safe, inside EEZ, near active fishing grounds."
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
    workflow.add_edge("synthesis" if False else "synthesizer", END)

    return workflow.compile()