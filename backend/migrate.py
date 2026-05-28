"""
migrate.py
----------
Script độc lập để tạo/đồng bộ toàn bộ schema CSDL.
Chạy trực tiếp: python migrate.py
Hoặc trong Docker: docker-compose exec backend python migrate.py
"""

import time
import logging
from database import engine, Base
# Import tất cả model để Base biết cần tạo bảng nào
from database import RagHistory, ChatSession, ChatMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_migration(max_retries: int = 10, delay: int = 3):
    """
    Chờ MySQL sẵn sàng rồi tạo toàn bộ bảng còn thiếu.
    Nếu bảng đã tồn tại, SQLAlchemy sẽ BỎ QUA (không xóa dữ liệu cũ).
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"⏳ Thử kết nối MySQL lần {attempt}/{max_retries}...")
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Migration hoàn tất! Các bảng đã được tạo/xác nhận:")
            for table_name in Base.metadata.tables:
                logger.info(f"   📋 {table_name}")
            return
        except Exception as e:
            logger.warning(f"   ❌ Lỗi: {e}")
            if attempt < max_retries:
                logger.info(f"   🔄 Thử lại sau {delay}s...")
                time.sleep(delay)

    logger.error("❌ Migration thất bại sau nhiều lần thử. Kiểm tra kết nối MySQL.")
    raise SystemExit(1)


if __name__ == "__main__":
    run_migration()
