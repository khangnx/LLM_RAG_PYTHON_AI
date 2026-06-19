import pandas as pd
from sqlalchemy import create_engine
import os
import sys

# Thêm đường dẫn backend vào sys.path để có thể import từ database.py
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    # Cố gắng import config từ database.py hiện tại
    from database import engine
except ImportError:
    # Fallback trong trường hợp cần thiết
    print("Warning: Không thể import cấu hình database hiện tại. Đang dùng cấu hình mặc định.")
    MYSQL_URL = "mysql+pymysql://root:123456@localhost:3306/real_estate_db"
    engine = create_engine(MYSQL_URL)

def load_real_estate_data() -> pd.DataFrame:
    """
    Kết nối vào MySQL và lấy toàn bộ dữ liệu từ bảng real_estate_dataset.
    Bảng này được kỳ vọng có các cột theo chuẩn tiếng Anh như:
    latitude, longitude, land_area, floors, interior_score, alley_width, raw_price_billion...
    """
    print("Đang kết nối tới CSDL MySQL để trích xuất dữ liệu...")
    query = "SELECT * FROM real_estate_dataset"
    try:
        df = pd.read_sql(query, con=engine)
        print(f"Trích xuất thành công {len(df)} bản ghi từ CSDL.")
        return df
    except Exception as e:
        print(f"Lỗi khi trích xuất dữ liệu: {e}")
        # Trả về DataFrame rỗng với cấu trúc chuẩn để không break code trong lúc test
        return pd.DataFrame(columns=[
            'id', 'latitude', 'longitude', 'land_area', 'floors', 
            'interior_score', 'alley_width', 'raw_price_billion', 'address'
        ])

if __name__ == "__main__":
    df = load_real_estate_data()
    print(df.head())
