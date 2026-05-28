"""
database.py
-----------
Module quản lý kết nối MySQL và định nghĩa tất cả model ORM.
Bảng:
  - rag_history    : Lưu audit log mỗi lần gọi /api/chat (giữ nguyên)
  - chat_sessions  : Mỗi cuộc trò chuyện biệt lập (UUID làm khóa chính)
  - chat_messages  : Từng tin nhắn thuộc về một session
"""

import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# =====================================================
# CẤU HÌNH KẾT NỐI DATABASE
# =====================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root_password@mysql:3306/rag_demo_db"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =====================================================
# MODEL: rag_history (AUDIT LOG - GIỮ NGUYÊN)
# =====================================================

class RagHistory(Base):
    """
    Bảng audit log - lưu mọi lượt chat để đối chiếu Prompt vs Response.
    """
    __tablename__ = "rag_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    search_query = Column(Text, nullable=False)
    generated_prompt = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# =====================================================
# MODEL: chat_sessions (QUẢN LÝ PHIÊN HỘI THOẠI)
# =====================================================

class ChatSession(Base):
    """
    Mỗi row là một cuộc trò chuyện biệt lập.
    id    : UUID dạng chuỗi (ví dụ: "550e8400-e29b-41d4-a716-446655440000")
    title : Tiêu đề phiên - tự động lấy từ câu hỏi đầu tiên.
    """
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="Cuộc trò chuyện mới")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ 1-nhiều với chat_messages, cascade xóa theo
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


# =====================================================
# MODEL: chat_messages (NỘI DUNG TỪNG TIN NHẮN)
# =====================================================

class ChatMessage(Base):
    """
    Từng tin nhắn trong một phiên hội thoại.
    role : 'user' hoặc 'ai'
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum("user", "ai", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ ngược về session
    session = relationship("ChatSession", back_populates="messages")


# =====================================================
# HÀM KHỞI TẠO DATABASE
# =====================================================

def init_db():
    """
    Tạo tất cả các bảng chưa tồn tại trong DB.
    Được gọi khi FastAPI khởi động.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI Dependency: Mở phiên DB, đảm bảo đóng sau khi dùng xong.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
