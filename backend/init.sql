-- ============================================================
-- FILE: init.sql
-- Mục đích: Khởi tạo schema cho database rag_demo_db
-- Bảng: rag_history - Lưu lịch sử mỗi lần user gọi API /api/chat
--
-- Lưu ý: File này chỉ để tham khảo hoặc import thủ công.
-- Backend FastAPI đã tự động tạo bảng này qua SQLAlchemy
-- (Base.metadata.create_all) khi khởi động lần đầu.
-- ============================================================

CREATE DATABASE IF NOT EXISTS rag_demo_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE rag_demo_db;

CREATE TABLE IF NOT EXISTS rag_history (
    -- Khóa chính, tự tăng
    id              INT             NOT NULL AUTO_INCREMENT,

    -- Câu hỏi gốc người dùng nhập vào (từ khóa tìm kiếm)
    search_query    LONGTEXT        NOT NULL,

    -- Toàn bộ Prompt hoàn chỉnh đã ráp Context + Câu hỏi gửi sang Ollama
    generated_prompt LONGTEXT       NOT NULL,

    -- Câu trả lời cuối cùng nhận về từ mô hình AI (Ollama/llama3)
    ai_response     LONGTEXT        NOT NULL,

    -- Thời điểm ghi log (UTC)
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
