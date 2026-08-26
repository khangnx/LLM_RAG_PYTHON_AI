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

def insert_sales_data_to_db(aggregated_json: dict) -> bool:
    """
    Nạp dữ liệu đã gộm cụm từ batch_processor vào bảng real_estate_dataset.
    Bước quan trọng: Geocoding address → lat/lon trước khi INSERT.
    """
    try:
        # --- GEOCODING: Địa chỉ chuỗi → Tọa độ (Bắt buộc cho XGBoost) ---
        address = aggregated_json.get("address", "")
        lat, lon = 10.7769, 106.7009  # Mặc định trung tâm TP.HCM

        if address:
            try:
                from app.services.geo_service import GeoService
                geo = GeoService()
                lat, lon = geo.get_coordinates(address)
                print(f"[Geocoding] '{address}' → lat={lat}, lon={lon}")
            except Exception as geo_err:
                print(f"[Geocoding] Không thể lấy tọa độ, dùng mặc định TP.HCM. Lỗi: {geo_err}")

        # --- GOM CỤM JSON đầy đủ các cột cần thiết cho bảng ---
        row = {
            "property_code":  aggregated_json.get("property_code", "UNKNOWN_PROPERTY"),
            "address":        aggregated_json.get("address"),
            "latitude":       lat,
            "longitude":      lon,
            "land_area":      aggregated_json.get("land_area", 50.0),
            "floors":         aggregated_json.get("floors", 1),
            "interior_score": aggregated_json.get("interior_score", 2),
            "alley_width":    aggregated_json.get("alley_width", 3.0),
            "raw_price_billion": aggregated_json.get("raw_price_billion", 0.0),  # Unlabelled → 0
            "data_source":    aggregated_json.get("data_source", "sales_upload"),
            "is_verified":    aggregated_json.get("is_verified", 1),
        }

        df = pd.DataFrame([row])
        df.to_sql("real_estate_dataset", con=engine, if_exists="append", index=False)
        print(f"[✅ DB] Đã INSERT thành công vào real_estate_dataset: {row['address']}")
        return True

    except Exception as e:
        print(f"[LỖI MySQL] Không thể lưu dữ liệu: {e}")
        return False
