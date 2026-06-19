from langgraph.graph import StateGraph, END
from app.agent_core.state import AgentState
from app.agent_core.nodes import (
    gatekeeper_router_node,
    estate_parsing_node,
    process_ml_and_rag_node,
    synthesize_report_node,
    general_doc_node
)

def route_request(state: AgentState):
    """
    Hàm định tuyến Conditional Edge dựa vào selected_tab
    """
    if state.get("selected_tab") == "estate_agent":
        return "estate_parsing"
    else:
        return "general_doc"

def build_agent_graph() -> StateGraph:
    """
    Biên dịch và khởi tạo luồng LangGraph với Router
    """
    workflow = StateGraph(AgentState)
    
    # Khai báo các Node
    workflow.add_node("gatekeeper", gatekeeper_router_node)
    
    # Nhánh 1: Estate Agent
    workflow.add_node("estate_parsing", estate_parsing_node)
    workflow.add_node("process_parallel", process_ml_and_rag_node)
    workflow.add_node("synthesize", synthesize_report_node)
    
    # Nhánh 2: General Doc
    workflow.add_node("general_doc", general_doc_node)
    
    # Khai báo Edges
    workflow.set_entry_point("gatekeeper")
    
    # Conditional Edge từ Gatekeeper
    workflow.add_conditional_edges(
        "gatekeeper",
        route_request,
        {
            "estate_parsing": "estate_parsing",
            "general_doc": "general_doc"
        }
    )
    
    # Luồng nhánh 1
    workflow.add_edge("estate_parsing", "process_parallel")
    workflow.add_edge("process_parallel", "synthesize")
    workflow.add_edge("synthesize", END)
    
    # Luồng nhánh 2
    workflow.add_edge("general_doc", END)
    
    # Biên dịch
    app = workflow.compile()
    
    return app

# Khởi tạo đối tượng graph app để sử dụng ở Router
agent_app = build_agent_graph()
