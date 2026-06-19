import os
import json
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from app.services.geo_service import GeoService
from app.services.ml_service import MLPredictorService
from app.services.rag_service import RAGService
from app.agent_core.state import AgentState

# Khởi tạo các Service
geo_service = GeoService()
ml_service = MLPredictorService()
rag_service = RAGService()

# Khởi tạo LLM Local
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
llm = ChatOllama(base_url=OLLAMA_HOST, model="qwen2.5:1.5b", temperature=0)

def gatekeeper_router_node(state: AgentState):
    """
    Node 0: Cổng điều phối đầu vào (Intent Parser & Router)
    """
    query = state["user_query"]
    has_media = bool(state.get("media_data"))
    
    system_prompt = """
Bạn là bộ não điều phối đầu vào (Intent Parser & Router) của hệ thống AI Agent nội bộ. Nhiệm vụ của bạn là phân tích câu hỏi của người dùng và các tệp tin đính kèm để định tuyến chính xác yêu cầu về 1 trong 2 phân vùng (Tab) chuyên biệt nhằm tối ưu hóa tài nguyên phần cứng local.

SYSTEM MODULES & TARGETS (ĐỊNH TUYẾN 2 MODULE):

1. Phân vùng 1: THẨM ĐỊNH BẤT ĐỘNG SẢN (estate_agent)
- Điều kiện kích hoạt: Người dùng tải lên hình ảnh/video tài sản, ảnh chụp sổ hồng, hoặc hỏi các câu hỏi liên quan đến định giá, vị trí địa lý, tọa độ, thông tin tính toán giá nhà đất.
- Mục tiêu xử lý: Kích hoạt luồng song song (Trích xuất thị giác PyTorch + Tính toán số học XGBoost).

2. Phân vùng 2: TRỢ LÝ TÀI LIỆU CHUNG (general_doc)
- Điều kiện kích hoạt: Người dùng hỏi, tra cứu hoặc đối chiếu thông tin dựa trên các tài liệu doanh nghiệp nội bộ (như file excel báo giá, dây chuyền lọc nước, dự toán nhà tiền chế, kế hoạch đầu tư...).
- Mục tiêu xử lý: Kích hoạt luồng Vector Search (RAG) trên tài liệu văn bản thông thường, không chạy qua mô hình định giá số học.

QUY TẮC ĐỊNH DẠNG ĐẦU RA (OUTPUT FORMAT RULES):
Bạn bắt buộc phải trả về kết quả dưới định dạng JSON thuần (không kèm markdown bao ngoài khối JSON). Cấu trúc JSON bắt buộc phải gồm các trường tổng quát sau:

{{
  "selected_tab": "estate_agent" hoặc "general_doc",
  "extracted_keywords": ["mảng các từ khóa chính trích xuất từ câu hỏi"],
  "has_media_input": true hoặc false,
  "routing_reason": "Đoạn văn ngắn giải thích lý do lựa chọn phân vùng xử lý nhằm tối ưu tốc độ local"
}}

BUSINESS EVENT LOGIC (LOGIC NGHIỆP VỤ):
- Hãy đánh giá kỹ lưỡng: Nếu câu hỏi có thể giải quyết nhanh bằng tài liệu doanh nghiệp (General Doc), tuyệt đối không định tuyến sang Estate Agent để tránh việc load nhầm các mô hình ma trận không gian nặng nề, giúp hệ thống chạy local đạt tốc độ tối đa.
- Không tự ý sinh thêm các trường dữ liệu nằm ngoài cấu trúc JSON quy định.
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", f"Câu hỏi: {query}\nCó file đính kèm: {has_media}")
    ])
    
    chain = prompt | llm.bind(format="json")
    response = chain.invoke({})
    
    try:
        parsed_json = json.loads(response.content)
    except Exception:
        parsed_json = {
            "selected_tab": "estate_agent" if has_media else "general_doc",
            "extracted_keywords": [],
            "has_media_input": has_media,
            "routing_reason": "Fallback do lỗi parse JSON"
        }
        
    return {
        "selected_tab": parsed_json.get("selected_tab", "general_doc"),
        "extracted_keywords": parsed_json.get("extracted_keywords", []),
        "routing_reason": parsed_json.get("routing_reason", "")
    }

def estate_parsing_node(state: AgentState):
    """
    Node 1 (BĐS): Phân tích ý định & Dữ liệu đầu vào
    """
    query = state["user_query"]
    media_data = state.get("media_data", {})
    
    system_prompt = """
    Bạn là một trợ lý ảo bóc tách dữ liệu bất động sản.
    Hãy đọc câu hỏi của người dùng và các thông tin đã được nhận diện từ hình ảnh (nếu có).
    Sau đó xuất ra DUY NHẤT một chuỗi JSON hợp lệ với cấu trúc sau:
    {{
        "address": "Địa chỉ hoặc tên đường, quận",
        "land_area": số (diện tích tính bằng m2),
        "floors": số (số tầng),
        "interior_score": số (1: Bình dân, 2: Trung bình, 3: Cao cấp)
    }}
    Nếu người dùng không cung cấp, hãy ưu tiên dùng dữ liệu từ media. Nếu cả 2 đều không có, để null.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", f"Câu hỏi: {query}\nDữ liệu Media: {json.dumps(media_data, ensure_ascii=False)}")
    ])
    
    chain = prompt | llm.bind(format="json")
    response = chain.invoke({})
    
    try:
        parsed_json = json.loads(response.content)
    except Exception:
        parsed_json = {
            "address": "TP.HCM",
            "land_area": media_data.get("land_area", 50.0) if isinstance(media_data, dict) else 50.0,
            "floors": media_data.get("floors", 1) if isinstance(media_data, dict) else 1,
            "interior_score": media_data.get("interior_score", 2) if isinstance(media_data, dict) else 2
        }
        
    return {"parsed_json": parsed_json}

def process_ml_and_rag_node(state: AgentState):
    """
    Node 2 (BĐS): Định tuyến Song song (Xử lý ML và RAG)
    """
    parsed_json = state.get("parsed_json", {})
    address = parsed_json.get("address", "")
    land_area = parsed_json.get("land_area", 50.0)
    floors = parsed_json.get("floors", 1)
    interior_score = parsed_json.get("interior_score", 2)
    
    lat, lon = geo_service.get_coordinates(address)
    predicted_price = ml_service.predict_price(
        latitude=lat,
        longitude=lon,
        land_area=land_area,
        floors=floors,
        interior_score=interior_score
    )
    
    zoning_context = rag_service.query_zoning_info(address)
    
    return {
        "coordinates": (lat, lon),
        "predicted_price": predicted_price,
        "zoning_context": zoning_context
    }

def synthesize_report_node(state: AgentState):
    """
    Node 3 (BĐS): Tổng hợp và Sinh Báo cáo Thẩm định BĐS
    """
    parsed_json = state.get("parsed_json", {})
    predicted_price = state.get("predicted_price", 0.0)
    zoning_context = state.get("zoning_context", "")
    
    system_prompt = """
    Bạn là chuyên gia thẩm định giá bất động sản. Hãy viết một báo cáo chuyên nghiệp, ngắn gọn.
    Dựa vào các số liệu sau:
    - Địa chỉ: {address}
    - Diện tích: {land_area} m2
    - Giá trị dự kiến (bởi AI): {price} Tỷ VNĐ
    - Thông tin quy hoạch: {zoning}
    
    Viết một đoạn tư vấn mượt mà bằng tiếng Việt.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt)
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "address": parsed_json.get("address", "Không xác định"),
        "land_area": parsed_json.get("land_area", 0),
        "price": predicted_price,
        "zoning": zoning_context
    })
    
    return {"final_report": response.content}

def general_doc_node(state: AgentState):
    """
    Node (Tài liệu chung): Tra cứu văn bản nội bộ không chạy ML
    """
    query = state["user_query"]
    keywords = state.get("extracted_keywords", [])
    search_query = " ".join(keywords) if keywords else query
    
    doc_context = rag_service.query_zoning_info(search_query) 
    
    system_prompt = """
    Bạn là một trợ lý ảo hỗ trợ nội bộ doanh nghiệp.
    Dựa vào tài liệu cung cấp, hãy trả lời câu hỏi của nhân viên một cách chính xác.
    
    Tài liệu: {context}
    Câu hỏi: {query}
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt)
    ])
    chain = prompt | llm
    response = chain.invoke({"context": doc_context, "query": query})
    
    return {"final_report": response.content}
