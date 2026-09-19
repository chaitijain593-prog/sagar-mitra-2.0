from langgraph.graph import StateGraph, END

# Import your real worker nodes
from app.sub_agents import navigation_node, fishing_node, compliance_node

# Import the Gemini advisory formatters to keep your persona and language features
from app.advisory import plain_gemini_answer, format_compliance_advisory

# 1. Define the shared state dictionary (The backpack that passes data between agents)
from app.state import AgentState

def create_orca_graph():
    workflow = StateGraph(AgentState)

    # 2. The Supervisor / Router Node (Decides who handles the task)
    # Compliance/legal keywords are checked first: a question like "am I
    # allowed to fish here" is a legal question, not a fishing one, even
    # though it contains "fish" -- checking fishing keywords first would
    # misroute it to the fishing node and skip the boundary/MPA check.
    COMPLIANCE_KEYWORDS = ("legal", "law", "boundary", "restrict", "allowed",
                           "permit", "protected area", "mpa", "eez", "compliance",
                           "violat")
    NAVIGATION_KEYWORDS = ("wave", "safe", "weather")
    FISHING_KEYWORDS = ("fish", "catch", "pfz")

    def supervisor_node(state: AgentState):
        print("--- SUPERVISOR: Routing user request ---")
        query = state.get("user_message", "").lower()

        if any(k in query for k in COMPLIANCE_KEYWORDS):
            state["next_step"] = "compliance"
        elif any(k in query for k in NAVIGATION_KEYWORDS):
            state["next_step"] = "navigation"
        elif any(k in query for k in FISHING_KEYWORDS):
            state["next_step"] = "fishing"
        else:
            state["next_step"] = "compliance"

        return state

    # 3. Synthesizer Node (Combines all reports at the end and formats via Gemini)
    def synthesizer_node(state: AgentState):
        print("--- SYNTHESIZER: Formatting final report via Gemini ---")
        raw_output = state.get("final_output", "Standard maritime check complete.")

        try:
            if state.get("next_step") == "compliance":
                # Legal/boundary findings must be reported exactly as computed --
                # route through the strict, non-inventive compliance formatter
                # instead of the general-knowledge fallback path.
                polished_advisory = format_compliance_advisory(
                    raw_report=raw_output,
                    persona="Fisherman",
                    language="English",
                )
            else:
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