from typing import TypedDict, Optional, Dict, Any, List

class AgentState(TypedDict):
    """
    Định nghĩa cấu trúc dữ liệu chạy xuyên suốt LangGraph.
    """
    user_query: str               # Câu hỏi ban đầu của user
    media_data: Optional[Dict]    # Dữ liệu media (ảnh, video) đã được phân tích bởi PyTorch
    
    # --- KẾT QUẢ TỪ GATEKEEPER ROUTER ---
    selected_tab: str             # "estate_agent" hoặc "general_doc"
    extracted_keywords: List[str]
    routing_reason: str
    
    # --- NHÁNH 1: ESTATE AGENT (THẨM ĐỊNH BĐS) ---
    parsed_json: Dict[str, Any]   # JSON bóc tách: address, land_area, floors, interior...
    coordinates: tuple            # (Lat, Long)
    predicted_price: float        # Giá dự báo từ XGBoost (Nhánh A)
    zoning_context: str           # Thông tin quy hoạch từ RAG (Nhánh B)
    
    # --- KẾT QUẢ CUỐI CÙNG ---
    final_report: str             # Bản báo cáo sinh bởi Ollama (dùng chung cho cả 2 tab)
