from fastapi import APIRouter, File, UploadFile, Form
from typing import Optional
from app.agent_core.graph import agent_app
from app.services.vision_service import VisionService

router = APIRouter()
vision_service = VisionService()

@router.post("/chat")
async def chat_with_agent(
    user_query: str = Form(..., description="Câu hỏi của người dùng"),
    media_file: Optional[UploadFile] = File(None, description="Hình ảnh/Video đính kèm (nếu có)")
):
    """
    Endpoint chính của Multimodal AI Agent.
    Tự động định tuyến (Gatekeeper) sang Tab Estate hoặc General Doc.
    """
    media_data = {}
    
    if media_file:
        file_bytes = await media_file.read()
        media_data = vision_service.process_media(file_bytes, media_file.filename)
        
    initial_state = {
        "user_query": user_query,
        "media_data": media_data,
        "selected_tab": "",
        "extracted_keywords": [],
        "routing_reason": "",
        "parsed_json": {},
        "coordinates": (0.0, 0.0),
        "predicted_price": 0.0,
        "zoning_context": "",
        "final_report": ""
    }
    
    # Chạy Graph
    result_state = agent_app.invoke(initial_state)
    
    # Chuẩn bị Response linh hoạt dựa trên Tab
    response_data = {
        "selected_tab": result_state.get("selected_tab"),
        "routing_reason": result_state.get("routing_reason"),
        "report": result_state.get("final_report")
    }
    
    # Nếu là tab thẩm định BĐS, trả về thêm số liệu
    if result_state.get("selected_tab") == "estate_agent":
        response_data.update({
            "parsed_info": result_state.get("parsed_json"),
            "coordinates": result_state.get("coordinates"),
            "predicted_price": result_state.get("predicted_price"),
            "extracted_media_features": media_data,
        })
        
    return {
        "status": "success",
        "data": response_data
    }
