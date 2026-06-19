import os
import json
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
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


def _safe_invoke(messages: list, use_json: bool = False) -> str:
    """
    Gọi LLM an toàn với danh sách messages trực tiếp (không qua template engine
    của LangChain) để tránh lỗi KeyError do ký tự {} trong nội dung.
    """
    try:
        if use_json:
            response = llm.bind(format="json").invoke(messages)
        else:
            response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"[LLM Error]: {str(e)}"


# =====================================================================
# NODE 0: GATEKEEPER ROUTER
# =====================================================================
def gatekeeper_router_node(state: AgentState):
    """
    Node 0: Cổng điều phối đầu vào - phân loại câu hỏi vào 2 luồng.
    """
    query = state["user_query"]
    has_media = bool(state.get("media_data"))

    system_text = (
        "Bạn là bộ não điều phối đầu vào (Intent Router).\n"
        "Phân loại câu hỏi thành 1 trong 2 luồng và trả về JSON:\n"
        "- \"estate_agent\": câu hỏi về định giá, mua bán, thuê nhà đất, bất động sản, hoặc có đính kèm ảnh nhà/sổ hồng.\n"
        "- \"general_doc\": câu hỏi về thông tin doanh nghiệp, nhân sự, báo giá sản phẩm, dự toán, quy trình nội bộ.\n\n"
        "Output JSON bắt buộc:\n"
        '{"selected_tab": "estate_agent" hoặc "general_doc", '
        '"extracted_keywords": ["kw1", "kw2"], '
        '"routing_reason": "lý do ngắn"}'
    )
    human_text = f"Câu hỏi: {query}\nCó file đính kèm: {has_media}"

    raw = _safe_invoke(
        [SystemMessage(content=system_text), HumanMessage(content=human_text)],
        use_json=True
    )

    try:
        parsed = json.loads(raw)
    except Exception:
        # Fallback: có media → BĐS, không có → tài liệu chung
        parsed = {
            "selected_tab": "estate_agent" if has_media else "general_doc",
            "extracted_keywords": [],
            "routing_reason": "Fallback do lỗi parse JSON từ LLM"
        }

    return {
        "selected_tab": parsed.get("selected_tab", "general_doc"),
        "extracted_keywords": parsed.get("extracted_keywords", []),
        "routing_reason": parsed.get("routing_reason", "")
    }


# =====================================================================
# NODE 1 (BĐS): PHÂN TÍCH DỮ LIỆU ĐẦU VÀO
# =====================================================================
def estate_parsing_node(state: AgentState):
    """
    Node 1: Bóc tách thông tin BĐS từ câu hỏi và dữ liệu media.
    Luôn dùng user_query gốc làm địa chỉ nếu LLM parse sai.
    """
    query = state["user_query"]
    media_data = state.get("media_data", {})
    media_str = json.dumps(media_data, ensure_ascii=False) if media_data else "Không có"

    system_text = (
        "Bạn là trợ lý bóc tách dữ liệu bất động sản.\n"
        "Đọc câu hỏi và trích xuất thông tin, xuất DUY NHẤT JSON:\n"
        '{"address": "chỉ tên đường/số nhà/quận/thành phố", "land_area": số_m2_hoặc_null, "floors": số_tầng_hoặc_null, "interior_score": 1_hoặc_2_hoặc_3_hoặc_null}\n'
        "QUAN TRỌNG: trường 'address' chỉ chứa địa chỉ bất động sản, KHÔNG chứa diện tích hay thông số kỹ thuật."
    )
    human_text = f"Câu hỏi: {query}\nDữ liệu Media: {media_str}"

    raw = _safe_invoke(
        [SystemMessage(content=system_text), HumanMessage(content=human_text)],
        use_json=True
    )

    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {}

    # ===== VALIDATION: Luôn kiểm tra và sửa lại address =====
    address = parsed.get("address", "") or ""
    # Nếu address rỗng, null, hoặc chứa từ kỹ thuật (m2, diện tích...) → dùng query gốc
    bad_keywords = ["m²", "m2", "diện tích", "tầng", "hầm", "null", "không"]
    if not address or any(kw in address.lower() for kw in bad_keywords) or len(address) < 5:
        address = query  # Fallback an toàn nhất: dùng toàn bộ câu hỏi gốc

    parsed["address"] = address
    parsed.setdefault("land_area", media_data.get("land_area", 50.0) if isinstance(media_data, dict) else 50.0)
    parsed.setdefault("floors", media_data.get("floors", 1) if isinstance(media_data, dict) else 1)
    parsed.setdefault("interior_score", media_data.get("interior_score", 2) if isinstance(media_data, dict) else 2)

    return {"parsed_json": parsed}


import re

def _safe_float(val, default=50.0):
    if val is None: return default
    if isinstance(val, (int, float)): return float(val)
    # Tìm kiếm các chữ số trong chuỗi (ví dụ: '48m2' -> 48.0)
    match = re.search(r"[-+]?\d*\.\d+|\d+", str(val))
    if match:
        return float(match.group())
    return default

def _safe_int(val, default=1):
    if val is None: return default
    if isinstance(val, (int, float)): return int(val)
    match = re.search(r"[-+]?\d+", str(val))
    if match:
        return int(match.group())
    return default

# =====================================================================
# NODE 2 (BĐS): XỬ LÝ ML + RAG QUY HOẠCH
# =====================================================================
def process_ml_and_rag_node(state: AgentState):
    """
    Node 2: Chạy XGBoost dự đoán giá và tra cứu quy hoạch từ VectorDB.
    """
    parsed_json = state.get("parsed_json", {})
    address = parsed_json.get("address") or state.get("user_query", "TP.HCM")
    
    # Ép kiểu an toàn bằng RegEx để chống lỗi ValueError: '48m2'
    land_area = _safe_float(parsed_json.get("land_area"), 50.0)
    floors = _safe_int(parsed_json.get("floors"), 1)
    interior_score = _safe_int(parsed_json.get("interior_score"), 2)

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


# =====================================================================
# NODE 3 (BĐS): TỔNG HỢP BÁO CÁO THẨM ĐỊNH
# =====================================================================
def synthesize_report_node(state: AgentState):
    """
    Node 3: Sinh báo cáo thẩm định BĐS từ dữ liệu THỰC TẾ.
    Prompt được thiết kế chặt chẽ để LLM KHÔNG được bịa thêm thông tin địa lý.
    """
    parsed_json = state.get("parsed_json", {})
    predicted_price = state.get("predicted_price", 0.0)
    coordinates = state.get("coordinates", (0.0, 0.0))
    zoning_context = state.get("zoning_context", "")
    user_query = state.get("user_query", "")

    address = parsed_json.get("address", user_query)
    land_area = parsed_json.get("land_area", "Không rõ")
    floors = parsed_json.get("floors", "Không rõ")
    lat, lon = coordinates if coordinates else ("N/A", "N/A")

    # Build structured data block — LLM chỉ được dùng đúng thông tin này
    data_block = (
        f"=== DỮ LIỆU THỰC TẾ TỪ HỆ THỐNG ===\n"
        f"Câu hỏi gốc của người dùng: {user_query}\n"
        f"Địa chỉ đã phân tích: {address}\n"
        f"Tọa độ geocoded: lat={lat}, lon={lon}\n"
        f"Diện tích đất: {land_area} m2\n"
        f"Số tầng: {floors}\n"
        f"Giá dự báo bởi XGBoost: {predicted_price} Tỷ VNĐ\n"
        f"Thông tin quy hoạch tìm được: {zoning_context if zoning_context else 'Không có trong cơ sở dữ liệu'}\n"
        f"======================================"
    )

    system_text = (
        "Bạn là chuyên gia thẩm định giá bất động sản.\n"
        "Hãy viết báo cáo thẩm định NGẮN GỌN dựa ĐÚNG và CHỈ dựa vào dữ liệu được cung cấp.\n"
        "NGHIÊM CẤM: Không được bịa đặt tên thành phố, tên đường, hoặc thông tin địa lý nào\n"
        "không có trong dữ liệu. Nếu thiếu thông tin, hãy ghi rõ 'Không có dữ liệu'.\n"
        "Cấu trúc báo cáo: 1. Thông tin tài sản | 2. Giá trị dự báo | 3. Lưu ý"
    )

    raw = _safe_invoke(
        [SystemMessage(content=system_text), HumanMessage(content=data_block)],
        use_json=False
    )

    return {"final_report": raw}


# =====================================================================
# NODE 4 (GENERAL DOC): TRA CỨU TÀI LIỆU NỘI BỘ
# =====================================================================
def general_doc_node(state: AgentState):
    """
    Node 4: Tra cứu tài liệu nội bộ qua RAG, không chạy qua ML pipeline BĐS.
    Dùng câu hỏi gốc (user_query) để search thay vì extracted_keywords
    nhằm giữ ngữ cảnh ngữ nghĩa đầy đủ cho VectorDB.
    """
    query = state["user_query"]

    # Dùng câu hỏi gốc để search, đảm bảo ngữ nghĩa đầy đủ
    doc_context = rag_service.query_general_docs(query)

    if doc_context:
        system_text = (
            "Bạn là trợ lý ảo hỗ trợ nội bộ doanh nghiệp.\n"
            "Dựa vào tài liệu dưới đây, hãy trả lời câu hỏi chính xác và ngắn gọn bằng tiếng Việt.\n"
            "Chỉ sử dụng thông tin có trong tài liệu. Không bịa đặt."
        )
        human_text = f"Tài liệu nội bộ:\n{doc_context}\n\nCâu hỏi: {query}"
    else:
        system_text = (
            "Bạn là trợ lý ảo hỗ trợ nội bộ doanh nghiệp.\n"
            "Thông báo lịch sự rằng không tìm thấy thông tin trong tài liệu nội bộ."
        )
        human_text = f"Câu hỏi: {query}\nKhông tìm thấy tài liệu liên quan."

    raw = _safe_invoke(
        [SystemMessage(content=system_text), HumanMessage(content=human_text)],
        use_json=False
    )

    return {"final_report": raw}
