from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

class RAGService:
    def __init__(self):
        self.persist_directory = self._resolve_persist_directory()

        # Load mô hình nhúng (Cần giống hệt mô hình dùng để Ingest trong main.py)
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")
            
            # Load ChromaDB
            self.vector_db = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            print(f"Đã nạp Vector DB thành công từ: {self.persist_directory}")
        except Exception as e:
            print(f"Lỗi khi nạp Vector DB từ {self.persist_directory}: {e}")
            self.vector_db = None

    def _resolve_persist_directory(self) -> str:
        default_dir = os.getenv("VECTOR_DB_DIR", "/vector_db")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(os.path.dirname(current_dir))
        local_fallback_dir = os.path.join(backend_dir, "vector_db")

        if os.path.exists(default_dir):
            return default_dir
        if os.path.exists(local_fallback_dir):
            return local_fallback_dir
        return default_dir

    def query_zoning_info(self, address_query: str) -> str:
        """
        Tra cứu quy hoạch dựa vào câu query (Tên đường, phường, quận).
        """
        if not self.vector_db:
            return "Không có thông tin quy hoạch do lỗi kết nối Vector DB."
            
        try:
            docs = self.vector_db.similarity_search(address_query, k=2)
            if docs:
                # Nối nội dung các văn bản quy hoạch tìm được
                return "\n".join([doc.page_content for doc in docs])
            else:
                return f"Không tìm thấy thông tin quy hoạch cụ thể cho khu vực: {address_query}."
        except Exception as e:
            return f"Lỗi tra cứu: {str(e)}"

    def query_general_docs(self, query: str) -> str:
        """
        Tra cứu tài liệu nội bộ chung, không đính kèm các câu cứng nhắc về quy hoạch.
        """
        if not self.vector_db:
            print("[RAGService] vector_db chưa nạp được.")
            return ""
            
        try:
            docs = self.vector_db.similarity_search(query, k=4)
            if docs:
                return "\n\n".join([doc.page_content for doc in docs])
            else:
                print(f"[RAGService] Không tìm thấy document với query: {query}")
                return ""
        except Exception as e:
            print(f"[RAGService] Lỗi query_general_docs: {e}")
            return ""
